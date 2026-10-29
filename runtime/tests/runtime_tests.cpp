// SPDX-License-Identifier: GPL-3.0-or-later
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <span>
#include <string>
#include <vector>

#include "rptp/runtime/elf_loader.hpp"
#include "rptp/runtime/guest_memory.hpp"

namespace {

using rptp::runtime::GuestMemory;
using rptp::runtime::kDefaultMaxGuestBytes;
using rptp::runtime::LoadErrorCode;
using rptp::runtime::LoadedSegment;
using rptp::runtime::LoadLimits;
using rptp::runtime::LoadOutcome;
using rptp::runtime::LoadReport;
using rptp::runtime::load_elf;
using rptp::runtime::to_string;

int failures = 0;

void check(bool condition, const char* expression, int line) {
  if (!condition) {
    std::cerr << "FAIL line " << line << ": " << expression << '\n';
    ++failures;
  }
}

#define CHECK(condition) check((condition), #condition, __LINE__)

void put16(std::vector<std::uint8_t>& image, std::size_t offset, std::uint16_t value) {
  image[offset] = static_cast<std::uint8_t>(value & 0xFFU);
  image[offset + 1] = static_cast<std::uint8_t>((value >> 8U) & 0xFFU);
}

void put32(std::vector<std::uint8_t>& image, std::size_t offset, std::uint32_t value) {
  image[offset] = static_cast<std::uint8_t>(value & 0xFFU);
  image[offset + 1] = static_cast<std::uint8_t>((value >> 8U) & 0xFFU);
  image[offset + 2] = static_cast<std::uint8_t>((value >> 16U) & 0xFFU);
  image[offset + 3] = static_cast<std::uint8_t>((value >> 24U) & 0xFFU);
}

std::uint32_t get32(const std::vector<std::uint8_t>& image, std::size_t offset) {
  return static_cast<std::uint32_t>(image[offset]) |
         (static_cast<std::uint32_t>(image[offset + 1]) << 8U) |
         (static_cast<std::uint32_t>(image[offset + 2]) << 16U) |
         (static_cast<std::uint32_t>(image[offset + 3]) << 24U);
}

struct SegmentSpec {
  std::uint32_t file_offset;
  std::uint32_t virtual_address;
  std::uint32_t file_size;
  std::uint32_t memory_size;
  std::uint32_t flags;
  std::uint32_t alignment;
};

std::vector<std::uint8_t> make_elf(std::uint32_t entry, const std::vector<SegmentSpec>& segments,
                                   std::size_t image_size = 0) {
  const std::size_t table_end = 52U + segments.size() * 32U;
  const std::size_t allocated = image_size != 0 ? image_size : std::max(table_end, std::size_t{148});
  std::vector<std::uint8_t> image(allocated, 0);
  image[0] = 0x7FU;
  image[1] = 'E';
  image[2] = 'L';
  image[3] = 'F';
  image[4] = 1;
  image[5] = 1;
  image[6] = 1;
  put16(image, 16, 2);
  put16(image, 18, 8);
  put32(image, 20, 1);
  put32(image, 24, entry);
  put32(image, 28, 52);
  put16(image, 40, 52);
  put16(image, 42, 32);
  put16(image, 44, static_cast<std::uint16_t>(segments.size()));
  for (std::size_t index = 0; index < segments.size(); ++index) {
    const SegmentSpec& spec = segments[index];
    const std::size_t base = 52U + index * 32U;
    put32(image, base, 1);
    put32(image, base + 4, spec.file_offset);
    put32(image, base + 8, spec.virtual_address);
    put32(image, base + 12, spec.virtual_address);
    put32(image, base + 16, spec.file_size);
    put32(image, base + 20, spec.memory_size);
    put32(image, base + 24, spec.flags);
    put32(image, base + 28, spec.alignment);
  }
  return image;
}

void write_bytes(std::vector<std::uint8_t>& image, std::size_t offset, std::span<const std::uint8_t> bytes) {
  std::copy(bytes.begin(), bytes.end(), image.begin() + static_cast<std::ptrdiff_t>(offset));
}

void expect_error(const LoadOutcome& outcome, LoadErrorCode expected, const char* label) {
  if (outcome.ok()) {
    std::cerr << "FAIL " << label << ": expected " << to_string(expected) << ", load succeeded\n";
    ++failures;
    return;
  }
  if (outcome.error->code != expected) {
    std::cerr << "FAIL " << label << ": expected " << to_string(expected) << ", got "
              << to_string(outcome.error->code) << " (" << outcome.error->message << ")\n";
    ++failures;
  }
  if (outcome.memory.region_count() != 0 || outcome.memory.mapped_bytes() != 0) {
    std::cerr << "FAIL " << label << ": failed load left guest memory populated\n";
    ++failures;
  }
}

bool same_report(const LoadReport& left, const LoadReport& right) {
  if (left.entry_point != right.entry_point || left.total_file_bytes != right.total_file_bytes ||
      left.total_memory_bytes != right.total_memory_bytes || left.segments.size() != right.segments.size()) {
    return false;
  }
  for (std::size_t index = 0; index < left.segments.size(); ++index) {
    const LoadedSegment& a = left.segments[index];
    const LoadedSegment& b = right.segments[index];
    if (a.program_header_index != b.program_header_index || a.file_offset != b.file_offset ||
        a.virtual_address != b.virtual_address || a.file_size != b.file_size ||
        a.memory_size != b.memory_size || a.flags != b.flags || a.alignment != b.alignment) {
      return false;
    }
  }
  return true;
}

void test_valid_two_segment_load() {
  const SegmentSpec code{120, 0x00100000, 4, 4, 5, 4};
  const SegmentSpec data{124, 0x00100010, 4, 8, 6, 4};
  std::vector<std::uint8_t> image = make_elf(0x00100000, {code, data});
  const std::array<std::uint8_t, 4> code_bytes{0x10, 0x20, 0x30, 0x40};
  const std::array<std::uint8_t, 4> data_bytes{0xAA, 0xBB, 0xCC, 0xDD};
  write_bytes(image, 120, code_bytes);
  write_bytes(image, 124, data_bytes);

  const LoadOutcome outcome = load_elf(image);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  CHECK(outcome.report.entry_point == 0x00100000U);
  CHECK(outcome.report.segments.size() == 2U);
  CHECK(outcome.report.total_file_bytes == 8U);
  CHECK(outcome.report.total_memory_bytes == 12U);
  CHECK(outcome.memory.region_count() == 2U);
  CHECK(outcome.memory.mapped_bytes() == 12U);
  CHECK(outcome.memory.max_bytes() == kDefaultMaxGuestBytes);
  if (outcome.report.segments.size() == 2U) {
    const LoadedSegment& loaded_code = outcome.report.segments[0];
    const LoadedSegment& loaded_data = outcome.report.segments[1];
    CHECK(loaded_code.program_header_index == 0U);
    CHECK(loaded_code.file_offset == 120U);
    CHECK(loaded_code.virtual_address == 0x00100000U);
    CHECK(loaded_code.file_size == 4U);
    CHECK(loaded_code.memory_size == 4U);
    CHECK(loaded_code.alignment == 4U);
    CHECK(loaded_code.executable());
    CHECK(!loaded_code.writable());
    CHECK(loaded_data.executable() == false);
    CHECK(loaded_data.writable());
  }

  std::array<std::uint8_t, 4> read_code{};
  CHECK(outcome.memory.read(0x00100000, read_code));
  CHECK(read_code == code_bytes);
  std::array<std::uint8_t, 8> read_data{};
  CHECK(outcome.memory.read(0x00100010, read_data));
  CHECK(read_data[0] == 0xAAU && read_data[1] == 0xBBU && read_data[2] == 0xCCU && read_data[3] == 0xDDU);
  CHECK(read_data[4] == 0U && read_data[5] == 0U && read_data[6] == 0U && read_data[7] == 0U);
  CHECK(outcome.memory.is_mapped(0x00100014, 4));
  CHECK(!outcome.memory.is_mapped(0x00100018, 1));
  CHECK(outcome.memory.view(0x00100000, 4).size() == 4U);
  CHECK(outcome.memory.view(0x0010001C, 4).empty());

  const LoadOutcome repeated = load_elf(image);
  CHECK(repeated.ok());
  if (repeated.ok()) {
    CHECK(same_report(outcome.report, repeated.report));
    std::array<std::uint8_t, 8> repeated_data{};
    CHECK(repeated.memory.read(0x00100010, repeated_data));
    CHECK(read_data == repeated_data);
  }
  CHECK(get32(image, 120) == 0x40302010U);
}

void test_header_errors() {
  const std::vector<std::uint8_t> tiny(10, 0);
  expect_error(load_elf(tiny), LoadErrorCode::ImageTooSmall, "truncated image");

  const SegmentSpec spec{84, 0x00100000, 4, 4, 5, 4};
  const std::vector<std::uint8_t> base = make_elf(0x00100000, {spec}, 84);

  {
    std::vector<std::uint8_t> image = base;
    image[1] = 'X';
    expect_error(load_elf(image), LoadErrorCode::NotElf, "bad magic");
  }
  {
    std::vector<std::uint8_t> image = base;
    image[4] = 2;
    expect_error(load_elf(image), LoadErrorCode::UnsupportedClass, "ELF64 class");
  }
  {
    std::vector<std::uint8_t> image = base;
    image[5] = 2;
    expect_error(load_elf(image), LoadErrorCode::UnsupportedEndianness, "big endian");
  }
  {
    std::vector<std::uint8_t> image = base;
    image[6] = 0;
    expect_error(load_elf(image), LoadErrorCode::VersionInvalid, "ident version");
  }
  {
    std::vector<std::uint8_t> image = base;
    put32(image, 20, 2);
    expect_error(load_elf(image), LoadErrorCode::VersionInvalid, "header version");
  }
  {
    std::vector<std::uint8_t> image = base;
    put16(image, 16, 3);
    expect_error(load_elf(image), LoadErrorCode::TypeInvalid, "type");
  }
  {
    std::vector<std::uint8_t> image = base;
    put16(image, 18, 3);
    expect_error(load_elf(image), LoadErrorCode::MachineInvalid, "machine");
  }
  {
    std::vector<std::uint8_t> image = base;
    put16(image, 40, 51);
    expect_error(load_elf(image), LoadErrorCode::HeaderSizeInvalid, "header size");
  }
  {
    std::vector<std::uint8_t> image = base;
    put16(image, 44, 257);
    expect_error(load_elf(image), LoadErrorCode::ProgramHeaderLimit, "program header limit");
  }
  {
    std::vector<std::uint8_t> image = base;
    put16(image, 42, 31);
    expect_error(load_elf(image), LoadErrorCode::ProgramHeadersOutOfBounds, "entry size");
  }
  {
    std::vector<std::uint8_t> image = base;
    put32(image, 28, 4);
    expect_error(load_elf(image), LoadErrorCode::ProgramHeadersOutOfBounds, "table before header");
  }
  {
    std::vector<std::uint8_t> image = base;
    put16(image, 44, 2);
    expect_error(load_elf(image), LoadErrorCode::ProgramHeadersOutOfBounds, "table past image");
  }
  {
    const std::vector<std::uint8_t> empty = make_elf(0x00100000, {});
    expect_error(load_elf(empty), LoadErrorCode::EntryUnmapped, "no program headers");
  }
}

void test_segment_errors() {
  {
    const SegmentSpec spec{84, 0x00100000, 8, 4, 5, 4};
    expect_error(load_elf(make_elf(0x00100000, {spec})), LoadErrorCode::SegmentSizeInvalid, "file larger than memory");
  }
  {
    const SegmentSpec spec{84, 0x00100000, 100, 100, 5, 4};
    expect_error(load_elf(make_elf(0x00100000, {spec})), LoadErrorCode::SegmentOutOfBounds, "payload past image");
  }
  {
    const SegmentSpec spec{84, 0x00100000, 4, 4, 5, 3};
    expect_error(load_elf(make_elf(0x00100000, {spec})), LoadErrorCode::SegmentAlignmentInvalid, "non power of two");
  }
  {
    const SegmentSpec spec{84, 0x00100000, 4, 4, 5, 4096};
    expect_error(load_elf(make_elf(0x00100000, {spec})), LoadErrorCode::SegmentAlignmentInvalid, "incongruent alignment");
  }
  {
    const SegmentSpec spec{84, 0xFFFFFFF0, 0, 0x20, 5, 1};
    expect_error(load_elf(make_elf(0xFFFFFFF0, {spec})), LoadErrorCode::SegmentAddressInvalid, "address overflow");
  }
  {
    const SegmentSpec first{84, 0x00002000, 4, 4, 5, 4};
    const SegmentSpec second{88, 0x00001000, 4, 4, 5, 4};
    expect_error(load_elf(make_elf(0x00002000, {first, second})), LoadErrorCode::SegmentOrderInvalid, "descending order");
  }
  {
    const SegmentSpec first{84, 0x00001000, 4, 0x20, 5, 4};
    const SegmentSpec second{88, 0x00001010, 4, 4, 5, 4};
    expect_error(load_elf(make_elf(0x00001000, {first, second})), LoadErrorCode::SegmentOverlap, "overlap");
  }
  {
    const SegmentSpec spec{84, 0x00001000, 4, 4, 5, 4};
    expect_error(load_elf(make_elf(0x00002000, {spec})), LoadErrorCode::EntryUnmapped, "entry outside segments");
  }
  {
    const SegmentSpec spec{84, 0x00100000, 4, 8, 5, 4};
    expect_error(load_elf(make_elf(0x00100004, {spec})), LoadErrorCode::EntryNotFileBacked, "entry in zero fill");
  }
  {
    const SegmentSpec spec{84, 0x00100000, 4, 4, 4, 4};
    expect_error(load_elf(make_elf(0x00100000, {spec})), LoadErrorCode::EntryNotExecutable, "entry not executable");
  }
  {
    std::vector<SegmentSpec> specs;
    for (std::uint32_t index = 0; index < 65; ++index) {
      specs.push_back(SegmentSpec{84, 0x00001000U + index * 0x100U, 0, 1, 5, 1});
    }
    expect_error(load_elf(make_elf(0x00001000, specs, 52U + 65U * 32U)), LoadErrorCode::SegmentLimit, "segment limit");
  }
}

void test_limits_and_zero_size_segment() {
  const SegmentSpec code{84, 0x00100000, 4, 4, 5, 4};
  const SegmentSpec data{88, 0x00100010, 4, 8, 6, 4};
  const std::vector<std::uint8_t> image = make_elf(0x00100000, {code, data});

  LoadLimits image_limit;
  image_limit.max_image_bytes = image.size() - 1U;
  expect_error(load_elf(image, image_limit), LoadErrorCode::ImageTooLarge, "image limit");

  LoadLimits guest_limit;
  guest_limit.max_guest_bytes = 11;
  expect_error(load_elf(image, guest_limit), LoadErrorCode::GuestLimit, "guest limit");

  LoadLimits bad_limits;
  bad_limits.max_guest_bytes = 0;
  expect_error(load_elf(image, bad_limits), LoadErrorCode::Internal, "zero limit");

  {
    const SegmentSpec empty{88, 0x00200000, 0, 0, 5, 1};
    const LoadOutcome outcome = load_elf(make_elf(0x00100000, {code, empty}));
    CHECK(outcome.ok());
    if (outcome.ok()) {
      CHECK(outcome.report.segments.size() == 2U);
      CHECK(outcome.report.total_memory_bytes == 4U);
      CHECK(outcome.memory.region_count() == 1U);
      CHECK(outcome.memory.mapped_bytes() == 4U);
    }
  }
}

void test_guest_memory_direct() {
  GuestMemory memory(16);
  CHECK(memory.max_bytes() == 16U);
  CHECK(memory.mapped_bytes() == 0U);
  CHECK(memory.region_count() == 0U);
  const std::array<std::uint8_t, 3> initial{1, 2, 3};
  CHECK(memory.map(0x1000, 8, initial));
  CHECK(memory.mapped_bytes() == 8U);
  CHECK(memory.region_count() == 1U);
  CHECK(memory.is_mapped(0x1000, 8));
  CHECK(!memory.is_mapped(0x1000, 9));
  CHECK(!memory.is_mapped(0x0FFF, 1));
  std::array<std::uint8_t, 8> buffer{};
  CHECK(memory.read(0x1000, buffer));
  CHECK(buffer[0] == 1U && buffer[1] == 2U && buffer[2] == 3U && buffer[3] == 0U && buffer[7] == 0U);
  const std::array<std::uint8_t, 2> patch{9, 9};
  CHECK(memory.write(0x1004, patch));
  std::array<std::uint8_t, 2> patched{};
  CHECK(memory.read(0x1004, patched));
  CHECK(patched[0] == 9U && patched[1] == 9U);
  CHECK(memory.write(0x1000, std::span<const std::uint8_t>(buffer).subspan(0, 8)));
  CHECK(!memory.map(0x1004, 4, initial));
  CHECK(memory.map(0x1008, 8, std::span<const std::uint8_t>{}));
  CHECK(memory.mapped_bytes() == 16U);
  CHECK(memory.region_count() == 2U);
  CHECK(!memory.map(0x1010, 1, std::span<const std::uint8_t>{}));
  CHECK(!memory.map(0xFFFFFFFF, 2, std::span<const std::uint8_t>{}));
  CHECK(!memory.map(0x2000, 0, std::span<const std::uint8_t>{}));
  CHECK(memory.view(0x1000, 8).size() == 8U);
  CHECK(memory.view(0x1004, 8).empty());
  CHECK(memory.view(0x1010, 1).empty());
}

}  // namespace

int main() {
  test_valid_two_segment_load();
  test_header_errors();
  test_segment_errors();
  test_limits_and_zero_size_segment();
  test_guest_memory_direct();
  if (failures != 0) {
    std::cerr << failures << " runtime loader check(s) failed\n";
    return 1;
  }
  std::cout << "runtime loader checks passed\n";
  return 0;
}
