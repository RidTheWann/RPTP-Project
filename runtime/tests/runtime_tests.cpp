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
#include "rptp/runtime/execution.hpp"
#include "rptp/runtime/guest_memory.hpp"

namespace {

using rptp::runtime::ExecErrorCode;
using rptp::runtime::ExecOptions;
using rptp::runtime::ExecOutcome;
using rptp::runtime::execute_loaded;
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

constexpr std::uint32_t kExecutableBase = 0x00100000U;
constexpr std::uint32_t kDataBase = 0x00002000U;

std::uint32_t encode_i(std::uint32_t op, std::uint32_t rs, std::uint32_t rt, std::int32_t immediate) {
  return ((op & 0x3FU) << 26U) | ((rs & 0x1FU) << 21U) | ((rt & 0x1FU) << 16U) |
         (static_cast<std::uint32_t>(immediate) & 0xFFFFU);
}

std::uint32_t encode_r(std::uint32_t rs, std::uint32_t rt, std::uint32_t rd, std::uint32_t shamt,
                       std::uint32_t funct) {
  return ((rs & 0x1FU) << 21U) | ((rt & 0x1FU) << 16U) | ((rd & 0x1FU) << 11U) | ((shamt & 0x1FU) << 6U) |
         (funct & 0x3FU);
}

std::uint32_t encode_j(std::uint32_t op, std::uint32_t target) {
  return ((op & 0x3FU) << 26U) | ((target >> 2U) & 0x03FFFFFFU);
}

std::vector<std::uint8_t> make_runnable_image(const std::vector<std::uint32_t>& code,
                                              std::uint32_t entry_offset = 0U,
                                              std::uint32_t data_memsz = 4U,
                                              std::span<const std::uint8_t> data = {}) {
  constexpr std::uint32_t kDataOffset = 0x100U;
  constexpr std::uint32_t kCodeOffset = 0x200U;
  const auto code_size = static_cast<std::uint32_t>(code.size() * sizeof(std::uint32_t));
  const auto data_file_size = static_cast<std::uint32_t>(data.empty() ? 4U : data.size());
  const SegmentSpec data_segment{kDataOffset, kDataBase, data_file_size,
                                 std::max(data_memsz, data_file_size), 6U, 4U};
  const SegmentSpec text{kCodeOffset, kExecutableBase, code_size, code_size, 5U, 4U};
  std::vector<std::uint8_t> image =
      make_elf(kExecutableBase + entry_offset, {data_segment, text}, kCodeOffset + code_size);
  for (std::size_t index = 0; index < code.size(); ++index) {
    put32(image, kCodeOffset + static_cast<std::uint32_t>(index) * 4U, code[index]);
  }
  if (!data.empty()) {
    write_bytes(image, kDataOffset, data);
  }
  return image;
}

ExecOutcome run_code(const std::vector<std::uint32_t>& code, const ExecOptions& options = {},
                     std::uint32_t data_memsz = 4U, std::span<const std::uint8_t> data = {}) {
  std::vector<std::uint8_t> image = make_runnable_image(code, 0U, data_memsz, data);
  LoadOutcome loaded = load_elf(image);
  if (!loaded.ok()) {
    std::cerr << "FAIL runnable image did not load: " << to_string(loaded.error->code) << '\n';
    ++failures;
    return {};
  }
  return execute_loaded(loaded.report, loaded.memory, options);
}

ExecOutcome run_high_code(const std::vector<std::uint32_t>& code, const ExecOptions& options = {}) {
  constexpr std::uint32_t kHighBase = 0xFFFFFFF0U;
  constexpr std::uint32_t kCodeOffset = 0x100U;
  const auto code_size = static_cast<std::uint32_t>(code.size() * sizeof(std::uint32_t));
  const SegmentSpec text{kCodeOffset, kHighBase, code_size, code_size, 5U, 4U};
  std::vector<std::uint8_t> image = make_elf(kHighBase, {text}, kCodeOffset + code_size);
  for (std::size_t index = 0; index < code.size(); ++index) {
    put32(image, kCodeOffset + static_cast<std::uint32_t>(index) * 4U, code[index]);
  }
  LoadOutcome loaded = load_elf(image);
  if (!loaded.ok()) {
    std::cerr << "FAIL high-address image did not load: " << to_string(loaded.error->code) << '\n';
    ++failures;
    return {};
  }
  return execute_loaded(loaded.report, loaded.memory, options);
}

void expect_exec_error(const ExecOutcome& outcome, ExecErrorCode expected, const char* label) {
  if (outcome.ok()) {
    std::cerr << "FAIL " << label << ": expected " << to_string(expected) << ", execution succeeded\n";
    ++failures;
    return;
  }
  if (outcome.error->code != expected) {
    std::cerr << "FAIL " << label << ": expected " << to_string(expected) << ", got "
              << to_string(outcome.error->code) << " (" << outcome.error->message << ")\n";
    ++failures;
  }
  if (outcome.result.steps != 0 || !outcome.result.trace.empty()) {
    std::cerr << "FAIL " << label << ": failed execution left a populated result\n";
    ++failures;
  }
}

void test_execution_arithmetic_and_memory() {
  const std::vector<std::uint32_t> code{
      encode_i(0x09, 0, 8, 7),        // addiu t0, zero, 7
      encode_i(0x09, 0, 9, 5),        // addiu t1, zero, 5
      encode_r(8, 9, 10, 0, 0x21),    // addu t2, t0, t1
      encode_i(0x09, 0, 11, 0x2000),  // addiu t3, zero, 0x2000
      encode_i(0x2B, 11, 10, 0),      // sw t2, 0(t3)
      encode_i(0x23, 11, 12, 0),      // lw t4, 0(t3)
      encode_i(0x09, 0, 13, -1),      // addiu t5, zero, -1
      encode_i(0x09, 0, 0, 1),        // addiu zero, zero, 1 (discarded)
  };
  const ExecOutcome outcome = run_code(code);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  CHECK(outcome.result.entry_point == kExecutableBase);
  CHECK(outcome.result.steps == code.size());
  CHECK(outcome.result.final_pc == kExecutableBase + 4U * static_cast<std::uint32_t>(code.size()));
  CHECK(outcome.result.halt_reason == rptp::runtime::HaltReason::UnmappedPc);
  CHECK(outcome.result.registers[8] == 7U);
  CHECK(outcome.result.registers[9] == 5U);
  CHECK(outcome.result.registers[10] == 12U);
  CHECK(outcome.result.registers[11] == 0x2000U);
  CHECK(outcome.result.registers[12] == 12U);
  CHECK(outcome.result.registers[13] == 0xFFFFFFFFFFFFFFFFULL);
  CHECK(outcome.result.registers[0] == 0U);
  CHECK(outcome.result.memory_writes.size() == 1U);
  if (outcome.result.memory_writes.size() == 1U) {
    CHECK(outcome.result.memory_writes[0].address == kDataBase);
    CHECK(outcome.result.memory_writes[0].value == 12U);
  }
}

void test_execution_branches_delay_slots_and_calls() {
  const std::vector<std::uint32_t> code{
      encode_i(0x09, 0, 8, 7),             // 0x00 addiu t0, zero, 7
      encode_i(0x09, 0, 9, 5),             // 0x04 addiu t1, zero, 5
      encode_r(8, 9, 10, 0, 0x21),         // 0x08 addu t2, t0, t1
      encode_i(0x09, 0, 11, 0x2000),       // 0x0c addiu t3, zero, 0x2000
      encode_i(0x2B, 11, 10, 0),           // 0x10 sw t2, 0(t3)
      encode_i(0x23, 11, 12, 0),           // 0x14 lw t4, 0(t3)
      encode_i(0x05, 10, 12, 5),           // 0x18 bne t2, t4, 0x30 (not taken)
      encode_i(0x09, 0, 16, 3),            // 0x1c addiu s0, zero, 3 (delay slot)
      encode_i(0x04, 10, 9, 4),            // 0x20 beq t2, t1, 0x34 (not taken)
      encode_i(0x09, 0, 17, 4),            // 0x24 addiu s1, zero, 4 (delay slot)
      encode_j(0x03, kExecutableBase + 0x48U),  // 0x28 jal 0x00100048
      encode_i(0x09, 0, 4, 9),             // 0x2c addiu a0, zero, 9 (delay slot)
      encode_i(0x09, 0, 18, 6),            // 0x30 addiu s2, zero, 6
      encode_j(0x02, kExecutableBase + 0x5CU),  // 0x34 j 0x0010005c
      encode_r(0, 0, 0, 0, 0),             // 0x38 nop (delay slot)
      encode_r(0, 0, 0, 0, 0),             // 0x3c nop
      encode_r(0, 0, 0, 0, 0),             // 0x40 nop
      encode_r(0, 0, 0, 0, 0),             // 0x44 nop
      encode_r(4, 10, 2, 0, 0x21),         // 0x48 addu v0, a0, t2
      encode_r(31, 0, 0, 0, 0x08),         // 0x4c jr ra
      encode_i(0x09, 0, 19, 8),            // 0x50 addiu s3, zero, 8 (delay slot)
      encode_r(0, 0, 0, 0, 0),             // 0x54 nop
      encode_r(0, 0, 0, 0, 0),             // 0x58 nop
      encode_i(0x09, 0, 20, 10),           // 0x5c addiu s4, zero, 10
  };
  ExecOptions options;
  options.trace = true;
  const ExecOutcome outcome = run_code(code, options);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  const std::vector<std::uint32_t> expected_trace{
      0x00100000U, 0x00100004U, 0x00100008U, 0x0010000CU, 0x00100010U, 0x00100014U, 0x00100018U,
      0x0010001CU, 0x00100020U, 0x00100024U, 0x00100028U, 0x0010002CU, 0x00100048U, 0x0010004CU,
      0x00100050U, 0x00100030U, 0x00100034U, 0x00100038U, 0x0010005CU};
  CHECK(outcome.result.trace == expected_trace);
  CHECK(outcome.result.steps == expected_trace.size());
  CHECK(outcome.result.final_pc == 0x00100060U);
  CHECK(outcome.result.registers[8] == 7U);
  CHECK(outcome.result.registers[9] == 5U);
  CHECK(outcome.result.registers[10] == 12U);
  CHECK(outcome.result.registers[11] == 0x2000U);
  CHECK(outcome.result.registers[12] == 12U);
  CHECK(outcome.result.registers[16] == 3U);
  CHECK(outcome.result.registers[17] == 4U);
  CHECK(outcome.result.registers[4] == 9U);
  CHECK(outcome.result.registers[2] == 21U);
  CHECK(outcome.result.registers[18] == 6U);
  CHECK(outcome.result.registers[19] == 8U);
  CHECK(outcome.result.registers[20] == 10U);
  CHECK(outcome.result.registers[31] == 0x00100030U);
  CHECK(outcome.result.memory_writes.size() == 1U);
}

enum class LikelyKind {
  Eq,
  Ne,
  Lez,
  Gtz,
  Ltz,
  Gez,
  Ltzal,
  Gzal,
};

struct LikelyFormSpec {
  const char* name;
  std::uint32_t opcode;
  std::uint32_t rt;
  LikelyKind kind;
  bool link;
};

void test_execution_likely_branch_forms() {
  const LikelyFormSpec forms[] = {
      {"beql", 0x14U, 0U, LikelyKind::Eq, false},
      {"bnel", 0x15U, 0U, LikelyKind::Ne, false},
      {"blezl", 0x16U, 0U, LikelyKind::Lez, false},
      {"bgtzl", 0x17U, 0U, LikelyKind::Gtz, false},
      {"bltzl", 0x01U, 0x02U, LikelyKind::Ltz, false},
      {"bgezl", 0x01U, 0x03U, LikelyKind::Gez, false},
      {"bltzall", 0x01U, 0x12U, LikelyKind::Ltzal, true},
      {"bgezall", 0x01U, 0x13U, LikelyKind::Gzal, true},
  };
  const bool outcomes[] = {false, true};
  for (const LikelyFormSpec& form : forms) {
    for (const bool taken : outcomes) {
      const auto expect = [&form, taken](bool condition, const char* what) {
        if (!condition) {
          std::cerr << "FAIL likely " << form.name << (taken ? " taken" : " not-taken") << ": " << what
                    << '\n';
          ++failures;
        }
      };
      std::int32_t t0 = 0;
      std::int32_t t1 = 0;
      switch (form.kind) {
        case LikelyKind::Eq:
          t0 = 1;
          t1 = taken ? 1 : 2;
          break;
        case LikelyKind::Ne:
          t0 = 1;
          t1 = taken ? 2 : 1;
          break;
        case LikelyKind::Lez:
          t0 = taken ? 0 : 1;
          break;
        case LikelyKind::Gtz:
          t0 = taken ? 1 : 0;
          break;
        case LikelyKind::Ltz:
        case LikelyKind::Ltzal:
          t0 = taken ? -1 : 0;
          break;
        case LikelyKind::Gez:
        case LikelyKind::Gzal:
          t0 = taken ? 0 : -1;
          break;
      }
      const std::uint32_t rt_field =
          (form.kind == LikelyKind::Eq || form.kind == LikelyKind::Ne) ? 9U : form.rt;
      const std::vector<std::uint32_t> code{
          encode_i(0x09, 0, 8, t0),
          encode_i(0x09, 0, 9, t1),
          encode_i(form.opcode, 8, rt_field, 2),
          encode_i(0x09, 0, 4, 0x11),
          encode_i(0x09, 0, 5, 0x22),
          encode_i(0x09, 0, 6, 0x33),
      };
      ExecOptions options;
      options.trace = true;
      const ExecOutcome outcome = run_code(code, options);
      if (!outcome.ok()) {
        std::cerr << "FAIL likely " << form.name << (taken ? " taken" : " not-taken")
                  << ": execution failed with " << to_string(outcome.error->code) << '\n';
        ++failures;
        continue;
      }
      expect(outcome.result.steps == 5U, "step count");
      expect(outcome.result.final_pc == kExecutableBase + 24U, "final pc");
      const std::vector<std::uint32_t> expected_trace{
          kExecutableBase, kExecutableBase + 4U, kExecutableBase + 8U,
          kExecutableBase + (taken ? 12U : 16U), kExecutableBase + 20U};
      expect(outcome.result.trace == expected_trace, "trace");
      expect(outcome.result.registers[4] == (taken ? 0x11U : 0U), "delay-slot register effect");
      expect(outcome.result.registers[5] == (taken ? 0U : 0x22U), "fall-through effect");
      expect(outcome.result.registers[6] == 0x33U, "target effect");
      expect(outcome.result.registers[0] == 0U, "zero register");
      if (form.link) {
        expect(outcome.result.registers[31] == kExecutableBase + 16U, "link address");
      } else {
        expect(outcome.result.registers[31] == 0U, "unexpected link");
      }
    }
  }
}

void test_execution_likely_combined_program() {
  const std::vector<std::uint32_t> code{
      encode_r(31, 0, 23, 0, 0x21),    // 0x00 addu s7, ra, zero
      encode_i(0x09, 0, 12, 0x2000),   // 0x04 addiu t4, zero, 0x2000
      encode_i(0x09, 0, 8, 1),         // 0x08 addiu t0, zero, 1
      encode_i(0x09, 0, 9, 1),         // 0x0c addiu t1, zero, 1
      encode_i(0x14, 8, 9, 2),         // 0x10 beql t0, t1, 0x1c (taken)
      encode_i(0x2B, 12, 9, 0),        // 0x14 sw t1, 0(t4) (delay slot)
      encode_i(0x09, 0, 2, 0x12),      // 0x18 addiu v0, zero, 0x12 (skipped)
      encode_i(0x09, 0, 8, 1),         // 0x1c addiu t0, zero, 1
      encode_i(0x09, 0, 9, 1),         // 0x20 addiu t1, zero, 1
      encode_i(0x15, 8, 9, 2),         // 0x24 bnel t0, t1, 0x30 (not taken)
      encode_i(0x2B, 12, 9, 4),        // 0x28 sw t1, 4(t4) (nullified)
      encode_i(0x09, 0, 3, 0x22),      // 0x2c addiu v1, zero, 0x22
      encode_i(0x09, 0, 8, 0),         // 0x30 addiu t0, zero, 0
      encode_i(0x16, 8, 0, 2),         // 0x34 blezl t0, 0x40 (taken)
      encode_i(0x09, 0, 4, 0x11),      // 0x38 addiu a0, zero, 0x11 (delay slot)
      encode_i(0x09, 0, 10, 0x12),     // 0x3c addiu t2, zero, 0x12 (skipped)
      encode_i(0x09, 0, 8, 0),         // 0x40 addiu t0, zero, 0
      encode_i(0x17, 8, 0, 2),         // 0x44 bgtzl t0, 0x50 (not taken)
      encode_i(0x09, 0, 5, 0x21),      // 0x48 addiu a1, zero, 0x21 (nullified)
      encode_i(0x09, 0, 11, 0x22),     // 0x4c addiu t3, zero, 0x22
      encode_i(0x09, 0, 8, 0),         // 0x50 addiu t0, zero, 0
      encode_i(0x01, 8, 0x02, 2),      // 0x54 bltzl t0, 0x60 (not taken)
      encode_i(0x09, 0, 6, 0x31),      // 0x58 addiu a2, zero, 0x31 (nullified)
      encode_i(0x09, 0, 13, 0x32),     // 0x5c addiu t5, zero, 0x32
      encode_i(0x09, 0, 8, 0),         // 0x60 addiu t0, zero, 0
      encode_i(0x01, 8, 0x03, 2),      // 0x64 bgezl t0, 0x70 (taken)
      encode_i(0x09, 0, 0, 7),         // 0x68 addiu zero, zero, 7 (delay slot)
      encode_i(0x09, 0, 14, 0x62),     // 0x6c addiu t6, zero, 0x62 (skipped)
      encode_i(0x09, 0, 8, -1),        // 0x70 addiu t0, zero, -1
      encode_i(0x01, 8, 0x12, 2),      // 0x74 bltzall t0, 0x80 (taken)
      encode_i(0x09, 0, 7, 0x41),      // 0x78 addiu a3, zero, 0x41 (delay slot)
      encode_i(0x09, 0, 15, 0x42),     // 0x7c addiu t7, zero, 0x42 (skipped)
      encode_i(0x09, 0, 8, -1),        // 0x80 addiu t0, zero, -1
      encode_i(0x01, 8, 0x13, 2),      // 0x84 bgezall t0, 0x90 (not taken)
      encode_i(0x09, 0, 16, 0x51),     // 0x88 addiu s0, zero, 0x51 (nullified)
      encode_i(0x09, 0, 24, 0x52),     // 0x8c addiu t8, zero, 0x52
      encode_r(23, 0, 0, 0, 0x08),     // 0x90 jr s7
      encode_r(0, 0, 0, 0, 0),         // 0x94 nop (delay slot)
  };
  ExecOptions options;
  options.trace = true;
  const ExecOutcome outcome = run_code(code, options);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  CHECK(outcome.result.steps == 30U);
  CHECK(outcome.result.final_pc == 0U);
  const std::vector<std::uint32_t> expected_trace{
      0x00100000U, 0x00100004U, 0x00100008U, 0x0010000CU, 0x00100010U, 0x00100014U,
      0x0010001CU, 0x00100020U, 0x00100024U, 0x0010002CU, 0x00100030U, 0x00100034U,
      0x00100038U, 0x00100040U, 0x00100044U, 0x0010004CU, 0x00100050U, 0x00100054U,
      0x0010005CU, 0x00100060U, 0x00100064U, 0x00100068U, 0x00100070U, 0x00100074U,
      0x00100078U, 0x00100080U, 0x00100084U, 0x0010008CU, 0x00100090U, 0x00100094U};
  CHECK(outcome.result.trace == expected_trace);
  CHECK(outcome.result.registers[0] == 0U);
  CHECK(outcome.result.registers[2] == 0U);
  CHECK(outcome.result.registers[3] == 0x22U);
  CHECK(outcome.result.registers[4] == 0x11U);
  CHECK(outcome.result.registers[5] == 0U);
  CHECK(outcome.result.registers[6] == 0U);
  CHECK(outcome.result.registers[7] == 0x41U);
  CHECK(outcome.result.registers[8] == 0xFFFFFFFFFFFFFFFFULL);
  CHECK(outcome.result.registers[9] == 1U);
  CHECK(outcome.result.registers[10] == 0U);
  CHECK(outcome.result.registers[11] == 0x22U);
  CHECK(outcome.result.registers[12] == 0x2000U);
  CHECK(outcome.result.registers[13] == 0x32U);
  CHECK(outcome.result.registers[14] == 0U);
  CHECK(outcome.result.registers[15] == 0U);
  CHECK(outcome.result.registers[16] == 0U);
  CHECK(outcome.result.registers[23] == 0U);
  CHECK(outcome.result.registers[24] == 0x52U);
  CHECK(outcome.result.registers[31] == kExecutableBase + 0x8CU);
  CHECK(outcome.result.memory_writes.size() == 1U);
  if (outcome.result.memory_writes.size() == 1U) {
    CHECK(outcome.result.memory_writes[0].address == kDataBase);
    CHECK(outcome.result.memory_writes[0].value == 1U);
  }
}

void test_execution_likely_nullification_and_failures() {
  ExecOptions traced;
  traced.trace = true;
  const ExecOutcome suppressed = run_code(
      {
          encode_i(0x09, 0, 8, 1),        // 0x00 addiu t0, zero, 1
          encode_i(0x09, 0, 9, 0x3000),   // 0x04 addiu t1, zero, 0x3000
          encode_i(0x15, 8, 8, 1),        // 0x08 bnel t0, t0, 0x10 (not taken)
          encode_i(0x2B, 9, 8, 0),        // 0x0c sw t0, 0(t1) (nullified, unmapped)
          encode_i(0x09, 0, 4, 0x22),     // 0x10 addiu a0, zero, 0x22
      },
      traced);
  CHECK(suppressed.ok());
  if (suppressed.ok()) {
    CHECK(suppressed.result.steps == 4U);
    CHECK(suppressed.result.final_pc == kExecutableBase + 0x14U);
    CHECK(suppressed.result.registers[4] == 0x22U);
    CHECK(suppressed.result.memory_writes.empty());
    const std::vector<std::uint32_t> expected_trace{
        kExecutableBase, kExecutableBase + 4U, kExecutableBase + 8U, kExecutableBase + 0x10U};
    CHECK(suppressed.result.trace == expected_trace);
  }

  expect_exec_error(
      run_code({encode_i(0x09, 0, 8, 1), encode_i(0x09, 0, 9, 0x3000), encode_i(0x14, 8, 8, 2),
                encode_i(0x2B, 9, 8, 0), encode_i(0x09, 0, 4, 0x22),
                encode_i(0x09, 0, 5, 0x33)}),
      ExecErrorCode::MemoryFault, "taken likely branch executes a faulting delay slot");

  ExecOptions tight;
  tight.max_steps = 1U;
  tight.trace = true;
  const ExecOutcome tight_outcome =
      run_code({encode_i(0x15, 8, 8, 1), encode_r(0, 0, 0, 0, 0)}, tight);
  CHECK(tight_outcome.ok());
  if (tight_outcome.ok()) {
    CHECK(tight_outcome.result.steps == 1U);
    CHECK(tight_outcome.result.final_pc == kExecutableBase + 8U);
    CHECK(tight_outcome.result.trace == std::vector<std::uint32_t>{kExecutableBase});
  }

  expect_exec_error(run_code({encode_i(0x01, 31, 0x12, 1), encode_r(0, 0, 0, 0, 0)}),
                    ExecErrorCode::UnsupportedInstruction, "bltzall with rs=31");
  expect_exec_error(run_code({encode_i(0x01, 31, 0x13, 1), encode_r(0, 0, 0, 0, 0)}),
                    ExecErrorCode::UnsupportedInstruction, "bgezall with rs=31");
  expect_exec_error(run_code({encode_i(0x15, 8, 8, 1), encode_j(0x02, kExecutableBase)}),
                    ExecErrorCode::DelaySlotControl, "control in a nullified delay slot");
  expect_exec_error(run_code({encode_i(0x15, 8, 8, 1), 0x00000015U}),
                    ExecErrorCode::UnsupportedInstruction, "unsupported word in a nullified delay slot");
  expect_exec_error(run_code({encode_i(0x15, 8, 8, 1)}), ExecErrorCode::DelaySlotMissing,
                    "missing nullified delay slot");

  const ExecOutcome rs31_non_link = run_code(
      {
          encode_i(0x01, 31, 0x02, 2),  // 0x00 bltzl ra, 0x0c (not taken; ra=0)
          encode_i(0x09, 0, 4, 0x11),   // 0x04 addiu a0, zero, 0x11 (nullified)
          encode_i(0x09, 0, 5, 0x22),   // 0x08 addiu a1, zero, 0x22
          encode_r(0, 0, 0, 0, 0),      // 0x0c nop
      },
      traced);
  CHECK(rs31_non_link.ok());
  if (rs31_non_link.ok()) {
    CHECK(rs31_non_link.result.registers[4] == 0U);
    CHECK(rs31_non_link.result.registers[5] == 0x22U);
    CHECK(rs31_non_link.result.registers[31] == 0U);
  }
}

void test_execution_likely_pc_masking() {
  constexpr std::uint32_t kHighBase = 0xFFFFFFF0U;
  ExecOptions options;
  options.trace = true;
  const ExecOutcome taken = run_high_code(
      {
          encode_i(0x09, 0, 8, 1),     // 0xFFFFFFF0 addiu t0, zero, 1
          encode_i(0x14, 8, 8, 4),     // 0xFFFFFFF4 beql t0, t0, +4 (wraps to 0x8)
          encode_i(0x09, 0, 4, 0x11),  // 0xFFFFFFF8 addiu a0, zero, 0x11 (delay slot)
          encode_i(0x09, 0, 5, 0x22),  // 0xFFFFFFFC addiu a1, zero, 0x22 (skipped)
      },
      options);
  CHECK(taken.ok());
  if (taken.ok()) {
    CHECK(taken.result.entry_point == kHighBase);
    CHECK(taken.result.final_pc == 8U);
    CHECK(taken.result.steps == 3U);
    CHECK(taken.result.registers[4] == 0x11U);
    CHECK(taken.result.registers[5] == 0U);
    const std::vector<std::uint32_t> expected{kHighBase, kHighBase + 4U, kHighBase + 8U};
    CHECK(taken.result.trace == expected);
  }

  const ExecOutcome not_taken = run_high_code(
      {
          encode_i(0x09, 0, 8, 1),     // 0xFFFFFFF0 addiu t0, zero, 1
          encode_i(0x15, 8, 8, 4),     // 0xFFFFFFF4 bnel t0, t0, +4 (not taken)
          encode_i(0x09, 0, 4, 0x11),  // 0xFFFFFFF8 addiu a0, zero, 0x11 (nullified)
          encode_i(0x09, 0, 5, 0x22),  // 0xFFFFFFFC addiu a1, zero, 0x22
      },
      options);
  CHECK(not_taken.ok());
  if (not_taken.ok()) {
    CHECK(not_taken.result.final_pc == 0U);
    CHECK(not_taken.result.steps == 3U);
    CHECK(not_taken.result.registers[4] == 0U);
    CHECK(not_taken.result.registers[5] == 0x22U);
    const std::vector<std::uint32_t> expected{kHighBase, kHighBase + 4U, kHighBase + 12U};
    CHECK(not_taken.result.trace == expected);
  }
}

enum class PlainKind {
  Lez,
  Gtz,
  Ltz,
  Gez,
};

struct PlainFormSpec {
  const char* name;
  std::uint32_t opcode;
  std::uint32_t rt;
  PlainKind kind;
  bool link;
};

void test_execution_plain_branch_forms() {
  const PlainFormSpec forms[] = {
      {"blez", 0x06U, 0U, PlainKind::Lez, false},
      {"bgtz", 0x07U, 0U, PlainKind::Gtz, false},
      {"bltz", 0x01U, 0x00U, PlainKind::Ltz, false},
      {"bgez", 0x01U, 0x01U, PlainKind::Gez, false},
      {"bltzal", 0x01U, 0x10U, PlainKind::Ltz, true},
      {"bgezal", 0x01U, 0x11U, PlainKind::Gez, true},
  };
  const bool outcomes[] = {false, true};
  for (const PlainFormSpec& form : forms) {
    for (const bool taken : outcomes) {
      const auto expect = [&form, taken](bool condition, const char* what) {
        if (!condition) {
          std::cerr << "FAIL plain " << form.name << (taken ? " taken" : " not-taken") << ": "
                    << what << '\n';
          ++failures;
        }
      };
      std::int32_t t0 = 0;
      switch (form.kind) {
        case PlainKind::Lez:
          t0 = taken ? 0 : 1;
          break;
        case PlainKind::Gtz:
          t0 = taken ? 1 : 0;
          break;
        case PlainKind::Ltz:
          t0 = taken ? -1 : 0;
          break;
        case PlainKind::Gez:
          t0 = taken ? 0 : -1;
          break;
      }
      const std::vector<std::uint32_t> code{
          encode_i(0x09, 0, 8, t0),
          encode_i(form.opcode, 8, form.rt, 2),
          encode_i(0x09, 0, 4, 0x11),
          encode_i(0x09, 0, 5, 0x22),
          encode_i(0x09, 0, 6, 0x33),
      };
      ExecOptions options;
      options.trace = true;
      const ExecOutcome outcome = run_code(code, options);
      if (!outcome.ok()) {
        std::cerr << "FAIL plain " << form.name << (taken ? " taken" : " not-taken")
                  << ": execution failed with " << to_string(outcome.error->code) << '\n';
        ++failures;
        continue;
      }
      expect(outcome.result.steps == (taken ? 4U : 5U), "step count");
      expect(outcome.result.final_pc == kExecutableBase + 20U, "final pc");
      std::vector<std::uint32_t> expected_trace{kExecutableBase, kExecutableBase + 4U,
                                                kExecutableBase + 8U};
      if (!taken) {
        expected_trace.push_back(kExecutableBase + 12U);
      }
      expected_trace.push_back(kExecutableBase + 16U);
      expect(outcome.result.trace == expected_trace, "trace");
      expect(outcome.result.registers[4] == 0x11U, "delay-slot register effect");
      expect(outcome.result.registers[5] == (taken ? 0U : 0x22U), "fall-through effect");
      expect(outcome.result.registers[6] == 0x33U, "target effect");
      expect(outcome.result.registers[0] == 0U, "zero register");
      if (form.link) {
        expect(outcome.result.registers[31] == kExecutableBase + 12U, "link address");
      } else {
        expect(outcome.result.registers[31] == 0U, "unexpected link");
      }
    }
  }
}

void test_execution_plain_branch_failures() {
  ExecOptions traced;
  traced.trace = true;
  expect_exec_error(run_code({encode_i(0x01, 31, 0x10, 1), encode_r(0, 0, 0, 0, 0)}),
                    ExecErrorCode::UnsupportedInstruction, "bltzal with rs=31");
  expect_exec_error(run_code({encode_i(0x01, 31, 0x11, 1), encode_r(0, 0, 0, 0, 0)}),
                    ExecErrorCode::UnsupportedInstruction, "bgezal with rs=31");
  expect_exec_error(run_code({encode_i(0x06, 8, 0, 1), encode_j(0x02, kExecutableBase)}),
                    ExecErrorCode::DelaySlotControl, "control in a plain-branch delay slot");

  const ExecOutcome rs31_non_link = run_code(
      {
          encode_i(0x06, 31, 0, 2),     // 0x00 blez ra, 0x0c (taken; ra=0)
          encode_i(0x09, 0, 4, 0x11),   // 0x04 addiu a0, zero, 0x11 (delay slot)
          encode_i(0x09, 0, 5, 0x22),   // 0x08 addiu a1, zero, 0x22 (skipped)
          encode_r(0, 0, 0, 0, 0),      // 0x0c nop
      },
      traced);
  CHECK(rs31_non_link.ok());
  if (rs31_non_link.ok()) {
    CHECK(rs31_non_link.result.registers[4] == 0x11U);
    CHECK(rs31_non_link.result.registers[5] == 0U);
    CHECK(rs31_non_link.result.registers[31] == 0U);
  }
}

void test_execution_extended_subset() {
  const std::vector<std::uint32_t> code{
      encode_r(0, 0, 31, 0, 0x21),      // 0x00 addu ra, zero, zero
      encode_i(0x09, 0, 8, 1),          // 0x04 addiu t0, zero, 1
      encode_i(0x0F, 0, 9, 0x8000),     // 0x08 lui t1, 0x8000
      encode_i(0x0F, 0, 10, 0x1234),    // 0x0c lui t2, 0x1234
      encode_i(0x0D, 10, 10, 0x5678),   // 0x10 ori t2, t2, 0x5678
      encode_i(0x0C, 10, 11, 0x00FF),   // 0x14 andi t3, t2, 0x00ff
      encode_i(0x0E, 10, 12, 0xFFFF),   // 0x18 xori t4, t2, 0xffff
      encode_r(0, 10, 13, 4, 0x00),     // 0x1c sll t5, t2, 4
      encode_r(9, 8, 14, 0, 0x2A),      // 0x20 slt t6, t1, t0
      encode_r(8, 9, 15, 0, 0x2B),      // 0x24 sltu t7, t0, t1
      encode_i(0x0A, 9, 16, -1),        // 0x28 slti s0, t1, -1
      encode_i(0x0B, 8, 17, -1),        // 0x2c sltiu s1, t0, -1
      encode_i(0x19, 9, 18, -1),        // 0x30 daddiu s2, t1, -1
      encode_r(10, 12, 19, 0, 0x24),    // 0x34 and s3, t2, t4
      encode_r(11, 13, 20, 0, 0x25),    // 0x38 or s4, t3, t5
      encode_r(9, 8, 21, 0, 0x26),      // 0x3c xor s5, t1, t0
      encode_r(8, 8, 22, 0, 0x27),      // 0x40 nor s6, t0, t0
      encode_i(0x09, 0, 23, 0x2000),    // 0x44 addiu s7, zero, 0x2000
      encode_i(0x2B, 23, 10, 0),        // 0x48 sw t2, 0(s7)
      encode_i(0x23, 23, 24, 0),        // 0x4c lw t8, 0(s7)
      encode_i(0x0F, 0, 25, 0x4000),    // 0x50 lui t9, 0x4000
      encode_r(0, 25, 26, 1, 0x00),     // 0x54 sll k0, t9, 1
      encode_r(26, 25, 27, 0, 0x2D),    // 0x58 daddu k1, k0, t9
      encode_r(26, 26, 28, 0, 0x2D),    // 0x5c daddu gp, k0, k0
      encode_r(8, 9, 0, 0, 0x2D),       // 0x60 daddu zero, t0, t1
      encode_r(8, 9, 2, 0, 0x23),       // 0x64 subu v0, t0, t1
      encode_r(9, 8, 3, 0, 0x23),       // 0x68 subu v1, t1, t0
      encode_r(10, 12, 4, 0, 0x23),     // 0x6c subu a0, t2, t4
      encode_r(0, 8, 5, 0, 0x23),       // 0x70 subu a1, zero, t0
      encode_r(8, 9, 0, 0, 0x23),       // 0x74 subu zero, t0, t1
      encode_r(0, 0, 0, 0, 0),          // 0x78 nop
  };
  const ExecOutcome outcome = run_code(code);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  CHECK(outcome.result.steps == code.size());
  CHECK(outcome.result.final_pc == kExecutableBase + 4U * static_cast<std::uint32_t>(code.size()));
  CHECK(outcome.result.registers[31] == 0U);
  CHECK(outcome.result.registers[8] == 1U);
  CHECK(outcome.result.registers[9] == 0xFFFFFFFF80000000ULL);
  CHECK(outcome.result.registers[10] == 0x12345678U);
  CHECK(outcome.result.registers[11] == 0x78U);
  CHECK(outcome.result.registers[12] == 0x1234A987U);
  CHECK(outcome.result.registers[13] == 0x23456780U);
  CHECK(outcome.result.registers[14] == 1U);
  CHECK(outcome.result.registers[15] == 1U);
  CHECK(outcome.result.registers[16] == 1U);
  CHECK(outcome.result.registers[17] == 1U);
  CHECK(outcome.result.registers[18] == 0xFFFFFFFF7FFFFFFFULL);
  CHECK(outcome.result.registers[19] == 0x12340000U);
  CHECK(outcome.result.registers[20] == 0x234567F8U);
  CHECK(outcome.result.registers[21] == 0xFFFFFFFF80000001ULL);
  CHECK(outcome.result.registers[22] == 0xFFFFFFFFFFFFFFFEULL);
  CHECK(outcome.result.registers[23] == 0x2000U);
  CHECK(outcome.result.registers[24] == 0x12345678U);
  CHECK(outcome.result.registers[25] == 0x40000000U);
  CHECK(outcome.result.registers[26] == 0xFFFFFFFF80000000ULL);
  CHECK(outcome.result.registers[27] == 0xFFFFFFFFC0000000ULL);
  CHECK(outcome.result.registers[28] == 0xFFFFFFFF00000000ULL);
  CHECK(outcome.result.registers[2] == 0xFFFFFFFF80000001ULL);
  CHECK(outcome.result.registers[3] == 0x000000007FFFFFFFULL);
  CHECK(outcome.result.registers[4] == 0xFFFFFFFFFFFFACF1ULL);
  CHECK(outcome.result.registers[5] == 0xFFFFFFFFFFFFFFFFULL);
  CHECK(outcome.result.registers[0] == 0U);
  CHECK(outcome.result.memory_writes.size() == 1U);
  if (outcome.result.memory_writes.size() == 1U) {
    CHECK(outcome.result.memory_writes[0].address == kDataBase);
    CHECK(outcome.result.memory_writes[0].value == 0x12345678U);
  }
}

void test_execution_doubleword_memory() {
  const std::vector<std::uint32_t> code{
      encode_i(0x0F, 0, 8, 0x8000),   // lui t0, 0x8000
      encode_i(0x09, 0, 9, 0x2000),   // addiu t1, zero, 0x2000
      encode_i(0x3F, 9, 8, 0),        // sd t0, 0(t1)
      encode_i(0x37, 9, 10, 0),       // ld t2, 0(t1)
      encode_i(0x37, 9, 0, 0),        // ld zero, 0(t1)
      encode_i(0x3F, 9, 0, 8),        // sd zero, 8(t1)
      encode_i(0x37, 9, 11, 8),       // ld t3, 8(t1)
      encode_r(0, 0, 0, 0, 0),        // nop
  };
  const ExecOutcome outcome = run_code(code, ExecOptions{}, 16U);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  CHECK(outcome.result.registers[8] == 0xFFFFFFFF80000000ULL);
  CHECK(outcome.result.registers[10] == 0xFFFFFFFF80000000ULL);
  CHECK(outcome.result.registers[11] == 0U);
  CHECK(outcome.result.registers[0] == 0U);
  CHECK(outcome.result.memory_writes.size() == 4U);
  if (outcome.result.memory_writes.size() == 4U) {
    CHECK(outcome.result.memory_writes[0].address == kDataBase);
    CHECK(outcome.result.memory_writes[0].value == 0x80000000U);
    CHECK(outcome.result.memory_writes[1].address == kDataBase + 4U);
    CHECK(outcome.result.memory_writes[1].value == 0xFFFFFFFFU);
    CHECK(outcome.result.memory_writes[2].address == kDataBase + 8U);
    CHECK(outcome.result.memory_writes[2].value == 0U);
    CHECK(outcome.result.memory_writes[3].address == kDataBase + 12U);
    CHECK(outcome.result.memory_writes[3].value == 0U);
  }

  expect_exec_error(
      run_code({encode_i(0x09, 0, 9, 0x2000), encode_i(0x3F, 9, 8, 8)}, ExecOptions{}, 12U),
      ExecErrorCode::MemoryFault, "doubleword store crossing the segment end");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 9, 0x2000), encode_i(0x37, 9, 8, 2)}, ExecOptions{}, 16U),
      ExecErrorCode::MemoryFault, "unaligned doubleword load");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 9, 0x2000), encode_i(0x3F, 9, 8, 4)}, ExecOptions{}, 16U),
      ExecErrorCode::MemoryFault, "unaligned doubleword store");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 9, 0x2000), encode_i(0x37, 9, 8, 0)}, ExecOptions{}, 4U),
      ExecErrorCode::MemoryFault, "doubleword load past the segment end");
  expect_exec_error(run_code({encode_i(0x36, 0, 8, 0)}), ExecErrorCode::UnsupportedInstruction,
                    "ldc2");
  expect_exec_error(run_code({encode_i(0x3E, 0, 8, 0)}), ExecErrorCode::UnsupportedInstruction,
                    "sdc2");
}

void test_execution_word_memory_alignment() {
  const std::vector<std::uint32_t> aligned_code{
      encode_i(0x0F, 0, 8, 0xAABB),   // lui t0, 0xAABB
      encode_i(0x0D, 8, 8, 0xCCDD),   // ori t0, t0, 0xCCDD
      encode_i(0x09, 0, 9, 0x2000),   // addiu t1, zero, 0x2000
      encode_i(0x2B, 9, 8, 0),        // sw t0, 0(t1)
      encode_i(0x23, 9, 10, 0),       // lw t2, 0(t1)
      encode_i(0x2B, 9, 8, 4),        // sw t0, 4(t1)
      encode_i(0x23, 9, 11, 4),       // lw t3, 4(t1)
  };
  const ExecOutcome aligned = run_code(aligned_code, ExecOptions{}, 8U);
  CHECK(aligned.ok());
  if (aligned.ok()) {
    CHECK(aligned.result.registers[8] == 0xFFFFFFFFAABBCCDDULL);
    CHECK(aligned.result.registers[10] == 0xFFFFFFFFAABBCCDDULL);
    CHECK(aligned.result.registers[11] == 0xFFFFFFFFAABBCCDDULL);
    CHECK(aligned.result.memory_writes.size() == 2U);
    if (aligned.result.memory_writes.size() == 2U) {
      CHECK(aligned.result.memory_writes[0].address == kDataBase);
      CHECK(aligned.result.memory_writes[0].value == 0xAABBCCDDU);
      CHECK(aligned.result.memory_writes[1].address == kDataBase + 4U);
      CHECK(aligned.result.memory_writes[1].value == 0xAABBCCDDU);
    }
  }

  const ExecOutcome unaligned_load =
      run_code({encode_i(0x09, 0, 9, 0x2000), encode_i(0x23, 9, 8, 2)}, ExecOptions{}, 8U);
  expect_exec_error(unaligned_load, ExecErrorCode::MemoryFault, "unaligned word load");
  if (!unaligned_load.ok()) {
    CHECK(unaligned_load.error->message.find("unaligned word load") != std::string::npos);
  }

  const ExecOutcome unaligned_store =
      run_code({encode_i(0x09, 0, 9, 0x2000), encode_i(0x2B, 9, 8, 2)}, ExecOptions{}, 8U);
  expect_exec_error(unaligned_store, ExecErrorCode::MemoryFault, "unaligned word store");
  if (!unaligned_store.ok()) {
    CHECK(unaligned_store.error->message.find("unaligned word store") != std::string::npos);
  }

  // An unaligned store must be rejected before any byte reaches memory.  The
  // data word starts as 0x11223344; a partial write at +2 would replace its
  // upper two bytes.
  std::vector<std::uint8_t> image = make_runnable_image(
      {encode_i(0x0F, 0, 8, 0xAABB), encode_i(0x0D, 8, 8, 0xCCDD),
       encode_i(0x09, 0, 9, 0x2000), encode_i(0x2B, 9, 8, 2)},
      0U, 8U);
  put32(image, 0x100U, 0x11223344U);
  LoadOutcome loaded = load_elf(image);
  CHECK(loaded.ok());
  if (loaded.ok()) {
    const ExecOutcome rejected = execute_loaded(loaded.report, loaded.memory);
    expect_exec_error(rejected, ExecErrorCode::MemoryFault, "unaligned word store is not partial");
    std::array<std::uint8_t, 4> bytes{};
    CHECK(loaded.memory.read(kDataBase, bytes));
    CHECK(bytes[0] == 0x44U);
    CHECK(bytes[1] == 0x33U);
    CHECK(bytes[2] == 0x22U);
    CHECK(bytes[3] == 0x11U);
  }
}

void test_execution_byte_and_half_memory() {
  const std::array<std::uint8_t, 16> data{
      0x80, 0x7F, 0x34, 0x12, 0x00, 0x80, 0x00, 0x00,
      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  };
  const std::vector<std::uint32_t> code{
      encode_i(0x09, 0, 11, 0x2000),  // addiu t3, zero, 0x2000
      encode_i(0x20, 11, 12, 0),      // lb t4, 0(t3)
      encode_i(0x24, 11, 13, 0),      // lbu t5, 0(t3)
      encode_i(0x20, 11, 14, 1),      // lb t6, 1(t3)
      encode_i(0x21, 11, 16, 4),      // lh s0, 4(t3)
      encode_i(0x25, 11, 17, 4),      // lhu s1, 4(t3)
      encode_i(0x21, 11, 18, 2),      // lh s2, 2(t3)
      encode_i(0x09, 0, 8, 0x55AA),   // addiu t0, zero, 0x55AA
      encode_i(0x28, 11, 8, 8),       // sb t0, 8(t3)
      encode_i(0x29, 11, 8, 10),      // sh t0, 10(t3)
      encode_i(0x2B, 11, 8, 12),      // sw t0, 12(t3)
      encode_i(0x24, 11, 9, 8),       // lbu t1, 8(t3)
      encode_i(0x25, 11, 10, 10),     // lhu t2, 10(t3)
      encode_i(0x23, 11, 4, 12),      // lw a0, 12(t3)
  };
  std::vector<std::uint8_t> image = make_runnable_image(code, 0U, 16U, data);
  LoadOutcome loaded = load_elf(image);
  CHECK(loaded.ok());
  if (!loaded.ok()) {
    return;
  }
  const ExecOutcome outcome = execute_loaded(loaded.report, loaded.memory);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    std::cerr << "FAIL byte and half execution: " << outcome.error->message << '\n';
    return;
  }
  CHECK(outcome.result.registers[11] == 0x2000U);
  CHECK(outcome.result.registers[12] == 0xFFFFFFFFFFFFFF80ULL);
  CHECK(outcome.result.registers[13] == 0x80U);
  CHECK(outcome.result.registers[14] == 0x7FU);
  CHECK(outcome.result.registers[16] == 0xFFFFFFFFFFFF8000ULL);
  CHECK(outcome.result.registers[17] == 0x8000U);
  CHECK(outcome.result.registers[18] == 0x1234U);
  CHECK(outcome.result.registers[8] == 0x55AAU);
  CHECK(outcome.result.registers[9] == 0xAAU);
  CHECK(outcome.result.registers[10] == 0x55AAU);
  CHECK(outcome.result.registers[4] == 0x55AAU);
  CHECK(outcome.result.registers[0] == 0U);
  CHECK(outcome.result.memory_writes.size() == 3U);
  if (outcome.result.memory_writes.size() == 3U) {
    CHECK(outcome.result.memory_writes[0].address == kDataBase + 8U);
    CHECK(outcome.result.memory_writes[0].value == 0xAAU);
    CHECK(outcome.result.memory_writes[0].width == 1U);
    CHECK(outcome.result.memory_writes[1].address == kDataBase + 10U);
    CHECK(outcome.result.memory_writes[1].value == 0x55AAU);
    CHECK(outcome.result.memory_writes[1].width == 2U);
    CHECK(outcome.result.memory_writes[2].address == kDataBase + 12U);
    CHECK(outcome.result.memory_writes[2].value == 0x55AAU);
    CHECK(outcome.result.memory_writes[2].width == 4U);
  }
  constexpr std::array<std::uint8_t, 16> kExpectedBytes{
      0x80, 0x7F, 0x34, 0x12, 0x00, 0x80, 0x00, 0x00,
      0xAA, 0x00, 0xAA, 0x55, 0xAA, 0x55, 0x00, 0x00,
  };
  std::array<std::uint8_t, 16> bytes{};
  CHECK(loaded.memory.read(kDataBase, bytes));
  CHECK(bytes == kExpectedBytes);

  const ExecOutcome unaligned_load =
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_i(0x21, 11, 12, 1)}, ExecOptions{}, 8U);
  expect_exec_error(unaligned_load, ExecErrorCode::MemoryFault, "unaligned halfword load");
  if (!unaligned_load.ok()) {
    CHECK(unaligned_load.error->message.find("unaligned halfword load") != std::string::npos);
  }
  const ExecOutcome unaligned_lhu =
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_i(0x25, 11, 12, 3)}, ExecOptions{}, 8U);
  expect_exec_error(unaligned_lhu, ExecErrorCode::MemoryFault, "unaligned unsigned halfword load");
  if (!unaligned_lhu.ok()) {
    CHECK(unaligned_lhu.error->message.find("unaligned halfword load") != std::string::npos);
  }
  const ExecOutcome unaligned_store =
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_i(0x29, 11, 8, 1)}, ExecOptions{}, 8U);
  expect_exec_error(unaligned_store, ExecErrorCode::MemoryFault, "unaligned halfword store");
  if (!unaligned_store.ok()) {
    CHECK(unaligned_store.error->message.find("unaligned halfword store") != std::string::npos);
  }
  expect_exec_error(
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_i(0x21, 11, 12, 6)}, ExecOptions{}, 7U),
      ExecErrorCode::MemoryFault, "halfword load crossing the segment end");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_i(0x29, 11, 8, 6)}, ExecOptions{}, 7U),
      ExecErrorCode::MemoryFault, "halfword store crossing the segment end");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_i(0x20, 11, 12, 7)}, ExecOptions{}, 7U),
      ExecErrorCode::MemoryFault, "byte load past the segment end");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_i(0x28, 11, 8, 7)}, ExecOptions{}, 7U),
      ExecErrorCode::MemoryFault, "byte store past the segment end");
  expect_exec_error(run_code({encode_i(0x22, 0, 8, 0)}), ExecErrorCode::UnsupportedInstruction,
                    "lwl");
  expect_exec_error(run_code({encode_i(0x26, 0, 8, 0)}), ExecErrorCode::UnsupportedInstruction,
                    "lwr");
  expect_exec_error(run_code({encode_i(0x2A, 0, 8, 0)}), ExecErrorCode::UnsupportedInstruction,
                    "swl");
  expect_exec_error(run_code({encode_i(0x2E, 0, 8, 0)}), ExecErrorCode::UnsupportedInstruction,
                    "swr");
}

void test_execution_doubleword_shifts() {
  const std::array<std::uint8_t, 24> data{
      0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80,  // 0x8000000000000001
      0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00,  // 0x0000000080000000
      0x00, 0x00, 0x00, 0x80, 0xFF, 0xFF, 0xFF, 0xFF,  // 0xFFFFFFFF80000000
  };
  const std::vector<std::uint32_t> code{
      encode_i(0x09, 0, 8, static_cast<std::int32_t>(kDataBase)),  // addiu t0, zero, data
      encode_i(0x37, 8, 9, 0),    // ld t1, 0(t0)
      encode_i(0x37, 8, 10, 8),   // ld t2, 8(t0)
      encode_i(0x37, 8, 11, 16),  // ld t3, 16(t0)
      encode_i(0x09, 0, 12, 1),   // addiu t4, zero, 1
      encode_i(0x09, 0, 13, 33),  // addiu t5, zero, 33
      encode_i(0x09, 0, 14, 65),  // addiu t6, zero, 65
      encode_r(0, 9, 15, 1, 0x38),    // dsll t7, t1, 1
      encode_r(0, 9, 16, 0, 0x3C),    // dsll32 s0, t1, 0
      encode_r(13, 9, 17, 0, 0x14),   // dsllv s1, t1, t5
      encode_r(0, 9, 18, 1, 0x3A),    // dsrl s2, t1, 1
      encode_r(0, 9, 19, 0, 0x3E),    // dsrl32 s3, t1, 0
      encode_r(14, 9, 20, 0, 0x16),   // dsrlv s4, t1, t6 (65 & 63 = 1)
      encode_r(0, 9, 21, 1, 0x3B),    // dsra s5, t1, 1
      encode_r(0, 11, 22, 0, 0x3F),   // dsra32 s6, t3, 0
      encode_r(12, 11, 26, 0, 0x17),  // dsrav k0, t3, t4
      encode_r(12, 10, 27, 0, 0x14),  // dsllv k1, t2, t4
      encode_r(12, 9, 0, 0, 0x14),    // dsllv zero, t1, t4 (discarded)
  };
  const ExecOutcome outcome = run_code(code, ExecOptions{}, 24U, data);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  CHECK(outcome.result.registers[9] == 0x8000000000000001ULL);
  CHECK(outcome.result.registers[10] == 0x0000000080000000ULL);
  CHECK(outcome.result.registers[11] == 0xFFFFFFFF80000000ULL);
  CHECK(outcome.result.registers[15] == 0x0000000000000002ULL);
  CHECK(outcome.result.registers[16] == 0x0000000100000000ULL);
  CHECK(outcome.result.registers[17] == 0x0000000200000000ULL);
  CHECK(outcome.result.registers[18] == 0x4000000000000000ULL);
  CHECK(outcome.result.registers[19] == 0x0000000080000000ULL);
  CHECK(outcome.result.registers[20] == 0x4000000000000000ULL);
  CHECK(outcome.result.registers[21] == 0xC000000000000000ULL);
  CHECK(outcome.result.registers[22] == 0xFFFFFFFFFFFFFFFFULL);
  CHECK(outcome.result.registers[26] == 0xFFFFFFFFC0000000ULL);
  CHECK(outcome.result.registers[27] == 0x0000000100000000ULL);
  CHECK(outcome.result.registers[0] == 0U);
  CHECK(outcome.result.memory_writes.empty());
}

void test_execution_doubleword_shift_failures() {
  expect_exec_error(run_code({encode_r(1, 9, 15, 1, 0x38)}), ExecErrorCode::UnsupportedInstruction,
                    "dsll with nonzero rs");
  expect_exec_error(run_code({encode_r(1, 9, 15, 0, 0x3C)}), ExecErrorCode::UnsupportedInstruction,
                    "dsll32 with nonzero rs");
  expect_exec_error(run_code({encode_r(1, 9, 15, 1, 0x3A)}), ExecErrorCode::UnsupportedInstruction,
                    "dsrl with nonzero rs");
  expect_exec_error(run_code({encode_r(1, 9, 15, 0, 0x3E)}), ExecErrorCode::UnsupportedInstruction,
                    "dsrl32 with nonzero rs");
  expect_exec_error(run_code({encode_r(1, 9, 15, 1, 0x3B)}), ExecErrorCode::UnsupportedInstruction,
                    "dsra with nonzero rs");
  expect_exec_error(run_code({encode_r(1, 9, 15, 0, 0x3F)}), ExecErrorCode::UnsupportedInstruction,
                    "dsra32 with nonzero rs");
  expect_exec_error(run_code({encode_r(13, 9, 15, 1, 0x14)}), ExecErrorCode::UnsupportedInstruction,
                    "dsllv with nonzero shamt");
  expect_exec_error(run_code({encode_r(13, 9, 15, 1, 0x16)}), ExecErrorCode::UnsupportedInstruction,
                    "dsrlv with nonzero shamt");
  expect_exec_error(run_code({encode_r(13, 9, 15, 1, 0x17)}), ExecErrorCode::UnsupportedInstruction,
                    "dsrav with nonzero shamt");
  expect_exec_error(run_code({encode_r(0, 9, 15, 0, 0x15)}), ExecErrorCode::UnsupportedInstruction,
                    "reserved SPECIAL funct 0x15");
}

void test_execution_hi_lo_state() {
  const std::vector<std::uint32_t> code{
      encode_i(0x09, 0, 8, 7),        // addiu t0, zero, 7
      encode_i(0x09, 0, 9, -3),       // addiu t1, zero, -3
      encode_i(0x09, 0, 3, 0x1234),   // addiu v1, zero, 0x1234
      encode_r(3, 0, 0, 0, 0x11),     // mthi v1
      encode_r(3, 0, 0, 0, 0x13),     // mtlo v1
      encode_r(0, 0, 4, 0, 0x10),     // mfhi a0
      encode_r(0, 0, 5, 0, 0x12),     // mflo a1
      encode_r(0, 0, 0, 0, 0x12),     // mflo zero (discarded)
      encode_r(8, 9, 10, 0, 0x18),    // mult t2, t0, t1 (rd := low 32 bits)
      encode_r(0, 0, 11, 0, 0x10),    // mfhi t3
      encode_r(0, 0, 12, 0, 0x12),    // mflo t4
      encode_i(0x09, 0, 13, -3),      // addiu t5, zero, -3
      encode_r(8, 13, 14, 0, 0x19),   // multu t6, t0, t5
      encode_r(0, 0, 15, 0, 0x10),    // mfhi t7
      encode_r(0, 0, 16, 0, 0x12),    // mflo s0
      encode_r(9, 8, 0, 0, 0x1A),     // div t1, t0 (-3 / 7)
      encode_r(0, 0, 17, 0, 0x10),    // mfhi s1
      encode_r(0, 0, 18, 0, 0x12),    // mflo s2
      encode_r(8, 9, 0, 0, 0x1A),     // div t0, t1 (7 / -3)
      encode_r(0, 0, 19, 0, 0x10),    // mfhi s3
      encode_r(0, 0, 20, 0, 0x12),    // mflo s4
      encode_r(9, 8, 0, 0, 0x1B),     // divu t1, t0
      encode_r(0, 0, 21, 0, 0x10),    // mfhi s5
      encode_r(0, 0, 22, 0, 0x12),    // mflo s6
      encode_r(8, 0, 0, 0, 0x1A),     // div t0, zero (division by zero)
      encode_r(0, 0, 23, 0, 0x10),    // mfhi s7
      encode_r(0, 0, 24, 0, 0x12),    // mflo t8
      encode_i(0x09, 0, 25, -32768),  // addiu t9, zero, 0xFFFF8000
      encode_r(0, 25, 25, 16, 0x00),  // sll t9, t9, 16
      encode_i(0x09, 0, 26, -1),      // addiu k0, zero, -1
      encode_r(25, 26, 0, 0, 0x1A),   // div t9, k0 (INT32_MIN / -1)
      encode_r(0, 0, 27, 0, 0x10),    // mfhi k1
      encode_r(0, 0, 28, 0, 0x12),    // mflo gp
      encode_r(25, 25, 29, 0, 0x18),  // mult sp, t9, t9
      encode_r(0, 0, 30, 0, 0x10),    // mfhi fp
      encode_r(0, 0, 31, 0, 0x12),    // mflo ra
      encode_r(31, 0, 0, 0, 0x08),    // jr ra (ra is zero: halt on unmapped PC)
      encode_r(0, 0, 0, 0, 0x00),     // nop (delay slot)
  };
  const ExecOutcome outcome = run_code(code);
  CHECK(outcome.ok());
  if (!outcome.ok()) {
    return;
  }
  CHECK(outcome.result.registers[0] == 0U);
  CHECK(outcome.result.registers[3] == 0x0000000000001234ULL);
  CHECK(outcome.result.registers[4] == 0x0000000000001234ULL);
  CHECK(outcome.result.registers[5] == 0x0000000000001234ULL);
  CHECK(outcome.result.registers[8] == 0x0000000000000007ULL);
  CHECK(outcome.result.registers[9] == 0xFFFFFFFFFFFFFFFDULL);
  CHECK(outcome.result.registers[10] == 0xFFFFFFFFFFFFFFEBULL);
  CHECK(outcome.result.registers[11] == 0xFFFFFFFFFFFFFFFFULL);
  CHECK(outcome.result.registers[12] == 0xFFFFFFFFFFFFFFEBULL);
  CHECK(outcome.result.registers[13] == 0xFFFFFFFFFFFFFFFDULL);
  CHECK(outcome.result.registers[14] == 0xFFFFFFFFFFFFFFEBULL);
  CHECK(outcome.result.registers[15] == 0x0000000000000006ULL);
  CHECK(outcome.result.registers[16] == 0xFFFFFFFFFFFFFFEBULL);
  CHECK(outcome.result.registers[17] == 0xFFFFFFFFFFFFFFFDULL);
  CHECK(outcome.result.registers[18] == 0x0000000000000000ULL);
  CHECK(outcome.result.registers[19] == 0x0000000000000001ULL);
  CHECK(outcome.result.registers[20] == 0xFFFFFFFFFFFFFFFEULL);
  CHECK(outcome.result.registers[21] == 0x0000000000000001ULL);
  CHECK(outcome.result.registers[22] == 0x0000000024924924ULL);
  CHECK(outcome.result.registers[23] == 0x0000000000000007ULL);
  CHECK(outcome.result.registers[24] == 0x0000000000000000ULL);
  CHECK(outcome.result.registers[25] == 0xFFFFFFFF80000000ULL);
  CHECK(outcome.result.registers[26] == 0xFFFFFFFFFFFFFFFFULL);
  CHECK(outcome.result.registers[27] == 0x0000000000000000ULL);
  CHECK(outcome.result.registers[28] == 0xFFFFFFFF80000000ULL);
  CHECK(outcome.result.registers[29] == 0x0000000000000000ULL);
  CHECK(outcome.result.registers[30] == 0x0000000040000000ULL);
  CHECK(outcome.result.registers[31] == 0x0000000000000000ULL);
  CHECK(outcome.result.hi == 0x0000000040000000ULL);
  CHECK(outcome.result.lo == 0x0000000000000000ULL);
  CHECK(outcome.result.memory_writes.empty());
}

void test_execution_hi_lo_failures() {
  expect_exec_error(run_code({encode_r(1, 0, 8, 0, 0x10)}), ExecErrorCode::UnsupportedInstruction,
                    "mfhi with nonzero rs");
  expect_exec_error(run_code({encode_r(0, 1, 8, 0, 0x12)}), ExecErrorCode::UnsupportedInstruction,
                    "mflo with nonzero rt");
  expect_exec_error(run_code({encode_r(0, 0, 8, 1, 0x10)}), ExecErrorCode::UnsupportedInstruction,
                    "mfhi with nonzero shamt");
  expect_exec_error(run_code({encode_r(0, 1, 0, 0, 0x11)}), ExecErrorCode::UnsupportedInstruction,
                    "mthi with nonzero rt");
  expect_exec_error(run_code({encode_r(1, 0, 8, 0, 0x13)}), ExecErrorCode::UnsupportedInstruction,
                    "mtlo with nonzero rd");
  expect_exec_error(run_code({encode_r(0, 0, 0, 1, 0x11)}), ExecErrorCode::UnsupportedInstruction,
                    "mthi with nonzero shamt");
  expect_exec_error(run_code({encode_r(8, 9, 10, 1, 0x18)}), ExecErrorCode::UnsupportedInstruction,
                    "mult with nonzero shamt");
  expect_exec_error(run_code({encode_r(8, 9, 10, 1, 0x19)}), ExecErrorCode::UnsupportedInstruction,
                    "multu with nonzero shamt");
  expect_exec_error(run_code({encode_r(8, 9, 10, 0, 0x1A)}), ExecErrorCode::UnsupportedInstruction,
                    "div with nonzero rd");
  expect_exec_error(run_code({encode_r(8, 9, 0, 1, 0x1B)}), ExecErrorCode::UnsupportedInstruction,
                    "divu with nonzero shamt");
}

void test_execution_failures() {
  expect_exec_error(run_code({0x00000015U}), ExecErrorCode::UnsupportedInstruction, "unsupported");
  expect_exec_error(run_code({encode_i(0x0F, 1, 8, 0)}), ExecErrorCode::UnsupportedInstruction,
                    "lui with nonzero rs");
  expect_exec_error(run_code({encode_r(1, 8, 9, 0, 0x00)}), ExecErrorCode::UnsupportedInstruction,
                    "sll with nonzero rs");
  expect_exec_error(run_code({encode_r(8, 9, 10, 1, 0x24)}), ExecErrorCode::UnsupportedInstruction,
                    "and with nonzero shamt");
  expect_exec_error(run_code({encode_r(8, 9, 10, 1, 0x2D)}), ExecErrorCode::UnsupportedInstruction,
                    "daddu with nonzero shamt");
  expect_exec_error(run_code({encode_r(8, 9, 10, 1, 0x23)}), ExecErrorCode::UnsupportedInstruction,
                    "subu with nonzero shamt");
  expect_exec_error(run_code({encode_r(8, 9, 10, 0, 0x22)}), ExecErrorCode::UnsupportedInstruction,
                    "trapping sub");
  expect_exec_error(run_code({encode_r(8, 9, 10, 0, 0x2E)}), ExecErrorCode::UnsupportedInstruction,
                    "dsubu");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 11, 0x2000), encode_r(11, 0, 0, 0, 0x08), encode_r(0, 0, 0, 0, 0)}),
      ExecErrorCode::PcNotExecutable, "jr into data");
  expect_exec_error(
      run_code({encode_i(0x09, 0, 8, 1), encode_i(0x09, 0, 11, 0x3000), encode_i(0x2B, 11, 8, 0)}),
      ExecErrorCode::MemoryFault, "store outside segments");
  expect_exec_error(
      run_code({encode_i(0x04, 0, 0, 2), encode_j(0x02, kExecutableBase), encode_r(0, 0, 0, 0, 0)}),
      ExecErrorCode::DelaySlotControl, "control in delay slot");
  expect_exec_error(run_code({encode_j(0x02, kExecutableBase)}), ExecErrorCode::DelaySlotMissing,
                    "missing delay slot");
  ExecOptions limited;
  limited.max_steps = 5U;
  limited.trace = true;
  const ExecOutcome limited_outcome =
      run_code({encode_j(0x02, kExecutableBase), encode_r(0, 0, 0, 0, 0)}, limited);
  expect_exec_error(limited_outcome, ExecErrorCode::StepLimit, "step limit");
  ExecOptions zero_budget;
  zero_budget.max_steps = 0U;
  expect_exec_error(run_code({encode_r(0, 0, 0, 0, 0)}, zero_budget), ExecErrorCode::Internal,
                    "zero step budget");

  std::vector<std::uint8_t> image = make_runnable_image({encode_r(0, 0, 0, 0, 0)}, 2U);
  LoadOutcome loaded = load_elf(image);
  CHECK(loaded.ok());
  if (loaded.ok()) {
    expect_exec_error(execute_loaded(loaded.report, loaded.memory), ExecErrorCode::EntryUnaligned,
                      "unaligned entry");
  }
}

void test_execution_is_deterministic() {
  const std::vector<std::uint32_t> code{
      encode_i(0x09, 0, 8, 3),
      encode_i(0x09, 0, 9, 4),
      encode_r(8, 9, 10, 0, 0x21),
  };
  ExecOptions options;
  options.trace = true;
  const ExecOutcome first = run_code(code, options);
  const ExecOutcome second = run_code(code, options);
  CHECK(first.ok());
  CHECK(second.ok());
  if (first.ok() && second.ok()) {
    CHECK(first.result.steps == second.result.steps);
    CHECK(first.result.final_pc == second.result.final_pc);
    CHECK(first.result.registers == second.result.registers);
    CHECK(first.result.trace == second.result.trace);
    CHECK(first.result.memory_writes.size() == second.result.memory_writes.size());
  }
}

}  // namespace

int main() {
  test_valid_two_segment_load();
  test_header_errors();
  test_segment_errors();
  test_limits_and_zero_size_segment();
  test_guest_memory_direct();
  test_execution_arithmetic_and_memory();
  test_execution_branches_delay_slots_and_calls();
  test_execution_likely_branch_forms();
  test_execution_likely_combined_program();
  test_execution_likely_nullification_and_failures();
  test_execution_likely_pc_masking();
  test_execution_plain_branch_forms();
  test_execution_plain_branch_failures();
  test_execution_extended_subset();
  test_execution_doubleword_memory();
  test_execution_doubleword_shifts();
  test_execution_doubleword_shift_failures();
  test_execution_hi_lo_state();
  test_execution_hi_lo_failures();
  test_execution_word_memory_alignment();
  test_execution_byte_and_half_memory();
  test_execution_failures();
  test_execution_is_deterministic();
  if (failures != 0) {
    std::cerr << failures << " runtime loader check(s) failed\n";
    return 1;
  }
  std::cout << "runtime loader and execution checks passed\n";
  return 0;
}
