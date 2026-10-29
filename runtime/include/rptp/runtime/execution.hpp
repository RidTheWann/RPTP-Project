// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef RPTP_RUNTIME_EXECUTION_HPP
#define RPTP_RUNTIME_EXECUTION_HPP

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "rptp/runtime/elf_loader.hpp"
#include "rptp/runtime/guest_memory.hpp"

namespace rptp::runtime {

inline constexpr std::size_t kDefaultMaxSteps = 1000000U;

enum class ExecErrorCode {
  EntryUnaligned,
  PcUnaligned,
  UnsupportedInstruction,
  PcNotExecutable,
  FetchFault,
  MemoryFault,
  DelaySlotControl,
  DelaySlotMissing,
  StepLimit,
  Internal,
};

[[nodiscard]] std::string_view to_string(ExecErrorCode code);

struct ExecError {
  ExecErrorCode code = ExecErrorCode::Internal;
  std::string message;
};

enum class HaltReason {
  UnmappedPc,
};

[[nodiscard]] std::string_view to_string(HaltReason reason);

struct ExecOptions {
  std::size_t max_steps = kDefaultMaxSteps;
  bool trace = false;
};

struct MemoryWrite {
  std::uint32_t address = 0;
  std::uint32_t value = 0;
};

struct ExecResult {
  std::uint32_t entry_point = 0;
  std::uint32_t final_pc = 0;
  HaltReason halt_reason = HaltReason::UnmappedPc;
  std::size_t steps = 0;
  std::array<std::uint64_t, 32> registers{};
  std::vector<MemoryWrite> memory_writes;
  std::vector<std::uint32_t> trace;
};

struct ExecOutcome {
  std::optional<ExecError> error;
  ExecResult result;

  [[nodiscard]] bool ok() const noexcept;
};

// Executes the accepted Gate 0 synthetic instruction subset on a loaded image.
// This is a differential-test harness, not a product interpreter: the guest is
// halted only when the next PC falls outside every loaded segment.
[[nodiscard]] ExecOutcome execute_loaded(const LoadReport& report, GuestMemory& memory,
                                         const ExecOptions& options = {});

}  // namespace rptp::runtime

#endif
