// SPDX-License-Identifier: GPL-3.0-or-later
#include "rptp/runtime/elf_loader.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace rptp::runtime {
namespace {

constexpr std::size_t kElfHeaderSize = 52;
constexpr std::size_t kProgramHeaderSize = 32;
constexpr std::uint16_t kTypeExec = 2;
constexpr std::uint16_t kMachineMips = 8;
constexpr std::uint32_t kSegmentTypeLoad = 1;
constexpr std::uint32_t kFlagExecute = 1;
constexpr std::uint32_t kFlagWrite = 2;

std::uint16_t read16(std::span<const std::uint8_t> image, std::size_t offset) {
  return static_cast<std::uint16_t>(image[offset]) |
         static_cast<std::uint16_t>(static_cast<std::uint16_t>(image[offset + 1]) << 8U);
}

std::uint32_t read32(std::span<const std::uint8_t> image, std::size_t offset) {
  return static_cast<std::uint32_t>(image[offset]) |
         (static_cast<std::uint32_t>(image[offset + 1]) << 8U) |
         (static_cast<std::uint32_t>(image[offset + 2]) << 16U) |
         (static_cast<std::uint32_t>(image[offset + 3]) << 24U);
}

LoadOutcome fail(LoadErrorCode code, std::string message) {
  return LoadOutcome{LoadError{code, std::move(message)}, LoadReport{}, GuestMemory{}};
}

struct ProgramSegment {
  std::uint32_t program_header_index = 0;
  std::uint32_t file_offset = 0;
  std::uint32_t virtual_address = 0;
  std::uint32_t file_size = 0;
  std::uint32_t memory_size = 0;
  std::uint32_t flags = 0;
  std::uint32_t alignment = 0;
};

}  // namespace

bool LoadedSegment::executable() const noexcept {
  return (flags & kFlagExecute) != 0;
}

bool LoadedSegment::writable() const noexcept {
  return (flags & kFlagWrite) != 0;
}

bool LoadOutcome::ok() const noexcept {
  return !error.has_value();
}

std::string_view to_string(LoadErrorCode code) {
  switch (code) {
    case LoadErrorCode::ImageTooSmall:
      return "LOAD_IMAGE_TOO_SMALL";
    case LoadErrorCode::ImageTooLarge:
      return "LOAD_IMAGE_TOO_LARGE";
    case LoadErrorCode::NotElf:
      return "LOAD_NOT_ELF";
    case LoadErrorCode::UnsupportedClass:
      return "LOAD_UNSUPPORTED_CLASS";
    case LoadErrorCode::UnsupportedEndianness:
      return "LOAD_UNSUPPORTED_ENDIANNESS";
    case LoadErrorCode::VersionInvalid:
      return "LOAD_VERSION_INVALID";
    case LoadErrorCode::TypeInvalid:
      return "LOAD_TYPE_INVALID";
    case LoadErrorCode::MachineInvalid:
      return "LOAD_MACHINE_INVALID";
    case LoadErrorCode::HeaderSizeInvalid:
      return "LOAD_HEADER_SIZE_INVALID";
    case LoadErrorCode::ProgramHeaderLimit:
      return "LOAD_PROGRAM_HEADER_LIMIT";
    case LoadErrorCode::ProgramHeadersOutOfBounds:
      return "LOAD_PROGRAM_HEADERS_OUT_OF_BOUNDS";
    case LoadErrorCode::SegmentLimit:
      return "LOAD_SEGMENT_LIMIT";
    case LoadErrorCode::SegmentOutOfBounds:
      return "LOAD_SEGMENT_OUT_OF_BOUNDS";
    case LoadErrorCode::SegmentSizeInvalid:
      return "LOAD_SEGMENT_SIZE_INVALID";
    case LoadErrorCode::SegmentAlignmentInvalid:
      return "LOAD_SEGMENT_ALIGNMENT_INVALID";
    case LoadErrorCode::SegmentAddressInvalid:
      return "LOAD_SEGMENT_ADDRESS_INVALID";
    case LoadErrorCode::SegmentOrderInvalid:
      return "LOAD_SEGMENT_ORDER_INVALID";
    case LoadErrorCode::SegmentOverlap:
      return "LOAD_SEGMENT_OVERLAP";
    case LoadErrorCode::EntryUnmapped:
      return "LOAD_ENTRY_UNMAPPED";
    case LoadErrorCode::EntryNotFileBacked:
      return "LOAD_ENTRY_NOT_FILE_BACKED";
    case LoadErrorCode::EntryNotExecutable:
      return "LOAD_ENTRY_NOT_EXECUTABLE";
    case LoadErrorCode::GuestLimit:
      return "LOAD_GUEST_LIMIT";
    case LoadErrorCode::MemoryConflict:
      return "LOAD_MEMORY_CONFLICT";
    case LoadErrorCode::Internal:
      return "LOAD_INTERNAL";
  }
  return "LOAD_INTERNAL";
}

LoadOutcome load_elf(std::span<const std::uint8_t> image, const LoadLimits& limits) {
  if (limits.max_image_bytes == 0 || limits.max_guest_bytes == 0 ||
      limits.max_program_headers == 0 || limits.max_load_segments == 0) {
    return fail(LoadErrorCode::Internal, "load limits must be positive");
  }
  if (image.size() > limits.max_image_bytes) {
    return fail(LoadErrorCode::ImageTooLarge,
                "image size " + std::to_string(image.size()) + " exceeds the configured limit of " +
                    std::to_string(limits.max_image_bytes) + " bytes");
  }
  if (image.size() < kElfHeaderSize) {
    return fail(LoadErrorCode::ImageTooSmall, "image is smaller than an ELF32 header");
  }
  if (!(image[0] == 0x7FU && image[1] == 'E' && image[2] == 'L' && image[3] == 'F')) {
    return fail(LoadErrorCode::NotElf, "image does not start with ELF magic");
  }
  if (image[4] != 1) {
    return fail(LoadErrorCode::UnsupportedClass, "only ELF32 images are supported");
  }
  if (image[5] != 1) {
    return fail(LoadErrorCode::UnsupportedEndianness, "only little-endian images are supported");
  }
  if (image[6] != 1 || read32(image, 20) != 1) {
    return fail(LoadErrorCode::VersionInvalid, "ELF version is not EV_CURRENT");
  }
  if (read16(image, 16) != kTypeExec) {
    return fail(LoadErrorCode::TypeInvalid, "only ET_EXEC images are supported");
  }
  if (read16(image, 18) != kMachineMips) {
    return fail(LoadErrorCode::MachineInvalid, "only EM_MIPS images are supported");
  }

  const std::size_t header_size = read16(image, 40);
  if (header_size < kElfHeaderSize || header_size > image.size()) {
    return fail(LoadErrorCode::HeaderSizeInvalid, "ELF header size is outside the image");
  }
  const std::size_t program_header_entry_size = read16(image, 42);
  const std::size_t program_header_count = read16(image, 44);
  const std::size_t program_header_offset = read32(image, 28);
  if (program_header_count > limits.max_program_headers) {
    return fail(LoadErrorCode::ProgramHeaderLimit,
                "program header count " + std::to_string(program_header_count) + " exceeds the configured limit");
  }
  if (program_header_count != 0) {
    const std::uint64_t table_end = static_cast<std::uint64_t>(program_header_offset) +
                                    static_cast<std::uint64_t>(program_header_entry_size) * program_header_count;
    if (program_header_entry_size < kProgramHeaderSize || program_header_offset < header_size ||
        table_end > image.size()) {
      return fail(LoadErrorCode::ProgramHeadersOutOfBounds, "ELF program header table is outside the image");
    }
  }

  std::vector<ProgramSegment> segments;
  std::uint64_t highest_memory_end = 0;
  std::uint32_t previous_address = 0;
  bool have_previous = false;
  std::uint64_t total_file_bytes = 0;
  std::uint64_t total_memory_bytes = 0;
  for (std::size_t index = 0; index < program_header_count; ++index) {
    const std::size_t offset = program_header_offset + index * program_header_entry_size;
    if (read32(image, offset) != kSegmentTypeLoad) {
      continue;
    }
    ProgramSegment segment;
    segment.program_header_index = static_cast<std::uint32_t>(index);
    segment.file_offset = read32(image, offset + 4);
    segment.virtual_address = read32(image, offset + 8);
    segment.file_size = read32(image, offset + 16);
    segment.memory_size = read32(image, offset + 20);
    segment.flags = read32(image, offset + 24);
    segment.alignment = read32(image, offset + 28);

    if (segment.file_size > segment.memory_size) {
      return fail(LoadErrorCode::SegmentSizeInvalid,
                  "PT_LOAD segment " + std::to_string(index) + " has a file size larger than its memory size");
    }
    if (static_cast<std::uint64_t>(segment.file_offset) + segment.file_size > image.size()) {
      return fail(LoadErrorCode::SegmentOutOfBounds,
                  "PT_LOAD segment " + std::to_string(index) + " extends beyond the image");
    }
    const std::uint32_t alignment = segment.alignment;
    if (alignment > 1 && (alignment & (alignment - 1)) != 0) {
      return fail(LoadErrorCode::SegmentAlignmentInvalid,
                  "PT_LOAD segment " + std::to_string(index) + " has a non-power-of-two alignment");
    }
    if (alignment > 1 && segment.virtual_address % alignment != segment.file_offset % alignment) {
      return fail(LoadErrorCode::SegmentAlignmentInvalid,
                  "PT_LOAD segment " + std::to_string(index) + " has an incongruent virtual address and file offset");
    }
    const std::uint64_t virtual_end = static_cast<std::uint64_t>(segment.virtual_address) + segment.memory_size;
    if (virtual_end > kGuestAddressSpaceSize) {
      return fail(LoadErrorCode::SegmentAddressInvalid,
                  "PT_LOAD segment " + std::to_string(index) + " overflows the 32-bit address space");
    }
    if (have_previous && segment.virtual_address < previous_address) {
      return fail(LoadErrorCode::SegmentOrderInvalid,
                  "PT_LOAD segment " + std::to_string(index) + " is not in ascending address order");
    }
    previous_address = segment.virtual_address;
    have_previous = true;
    if (segment.memory_size != 0) {
      if (segment.virtual_address < highest_memory_end) {
        return fail(LoadErrorCode::SegmentOverlap,
                    "PT_LOAD segment " + std::to_string(index) + " overlaps an earlier segment");
      }
      highest_memory_end = std::max(highest_memory_end, virtual_end);
    }
    if (segments.size() >= limits.max_load_segments) {
      return fail(LoadErrorCode::SegmentLimit,
                  "PT_LOAD segment count exceeds the configured limit of " +
                      std::to_string(limits.max_load_segments));
    }
    total_file_bytes += segment.file_size;
    total_memory_bytes += segment.memory_size;
    segments.push_back(segment);
  }

  if (total_memory_bytes > limits.max_guest_bytes) {
    return fail(LoadErrorCode::GuestLimit,
                "PT_LOAD memory size " + std::to_string(total_memory_bytes) + " exceeds the configured limit of " +
                    std::to_string(limits.max_guest_bytes) + " bytes");
  }

  const std::uint32_t entry_point = read32(image, 24);
  const ProgramSegment* entry_segment = nullptr;
  for (const ProgramSegment& segment : segments) {
    if (segment.memory_size == 0) {
      continue;
    }
    const std::uint64_t virtual_end = static_cast<std::uint64_t>(segment.virtual_address) + segment.memory_size;
    if (segment.virtual_address <= entry_point && static_cast<std::uint64_t>(entry_point) < virtual_end) {
      entry_segment = &segment;
      break;
    }
  }
  if (entry_segment == nullptr) {
    return fail(LoadErrorCode::EntryUnmapped, "entry point is not inside a PT_LOAD memory range");
  }
  if (static_cast<std::uint64_t>(entry_point) >=
      static_cast<std::uint64_t>(entry_segment->virtual_address) + entry_segment->file_size) {
    return fail(LoadErrorCode::EntryNotFileBacked, "entry point is in a zero-filled PT_LOAD range");
  }
  if ((entry_segment->flags & kFlagExecute) == 0) {
    return fail(LoadErrorCode::EntryNotExecutable, "entry point is not inside an executable PT_LOAD segment");
  }

  LoadReport report;
  report.entry_point = entry_point;
  report.total_file_bytes = total_file_bytes;
  report.total_memory_bytes = total_memory_bytes;
  report.segments.reserve(segments.size());
  for (const ProgramSegment& segment : segments) {
    report.segments.push_back(LoadedSegment{segment.program_header_index, segment.file_offset,
                                            segment.virtual_address, segment.file_size, segment.memory_size,
                                            segment.flags, segment.alignment});
  }

  GuestMemory memory(limits.max_guest_bytes);
  for (const ProgramSegment& segment : segments) {
    if (segment.memory_size == 0) {
      continue;
    }
    const auto payload = image.subspan(segment.file_offset, segment.file_size);
    if (!memory.map(segment.virtual_address, segment.memory_size, payload)) {
      return fail(LoadErrorCode::MemoryConflict,
                  "failed to map PT_LOAD segment " + std::to_string(segment.program_header_index));
    }
  }
  return LoadOutcome{std::nullopt, std::move(report), std::move(memory)};
}

}  // namespace rptp::runtime
