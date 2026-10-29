// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef RPTP_RUNTIME_ELF_LOADER_HPP
#define RPTP_RUNTIME_ELF_LOADER_HPP

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "rptp/runtime/guest_memory.hpp"

namespace rptp::runtime {

inline constexpr std::size_t kDefaultMaxImageBytes = 16U * 1024U * 1024U;
inline constexpr std::uint32_t kDefaultMaxLoadSegments = 64;
inline constexpr std::uint32_t kDefaultMaxProgramHeaders = 256;

enum class LoadErrorCode {
  ImageTooSmall,
  ImageTooLarge,
  NotElf,
  UnsupportedClass,
  UnsupportedEndianness,
  VersionInvalid,
  TypeInvalid,
  MachineInvalid,
  HeaderSizeInvalid,
  ProgramHeaderLimit,
  ProgramHeadersOutOfBounds,
  SegmentLimit,
  SegmentOutOfBounds,
  SegmentSizeInvalid,
  SegmentAlignmentInvalid,
  SegmentAddressInvalid,
  SegmentOrderInvalid,
  SegmentOverlap,
  EntryUnmapped,
  EntryNotFileBacked,
  EntryNotExecutable,
  GuestLimit,
  MemoryConflict,
  Internal,
};

[[nodiscard]] std::string_view to_string(LoadErrorCode code);

struct LoadError {
  LoadErrorCode code = LoadErrorCode::Internal;
  std::string message;
};

struct LoadedSegment {
  std::uint32_t program_header_index = 0;
  std::uint32_t file_offset = 0;
  std::uint32_t virtual_address = 0;
  std::uint32_t file_size = 0;
  std::uint32_t memory_size = 0;
  std::uint32_t flags = 0;
  std::uint32_t alignment = 0;

  [[nodiscard]] bool executable() const noexcept;
  [[nodiscard]] bool writable() const noexcept;
};

struct LoadReport {
  std::uint32_t entry_point = 0;
  std::vector<LoadedSegment> segments;
  std::uint64_t total_file_bytes = 0;
  std::uint64_t total_memory_bytes = 0;
};

struct LoadLimits {
  std::size_t max_image_bytes = kDefaultMaxImageBytes;
  std::size_t max_guest_bytes = kDefaultMaxGuestBytes;
  std::uint32_t max_program_headers = kDefaultMaxProgramHeaders;
  std::uint32_t max_load_segments = kDefaultMaxLoadSegments;
};

struct LoadOutcome {
  std::optional<LoadError> error;
  LoadReport report;
  GuestMemory memory;

  [[nodiscard]] bool ok() const noexcept;
};

// Validates an ELF32 little-endian EM_MIPS ET_EXEC image and materializes only
// its PT_LOAD segments. The input is never modified; on error the returned
// memory is empty and the report is not meaningful.
[[nodiscard]] LoadOutcome load_elf(std::span<const std::uint8_t> image, const LoadLimits& limits = {});

}  // namespace rptp::runtime

#endif
