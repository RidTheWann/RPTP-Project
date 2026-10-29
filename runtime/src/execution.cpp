// SPDX-License-Identifier: GPL-3.0-or-later
#include "rptp/runtime/execution.hpp"

#include <array>
#include <cstdio>
#include <map>
#include <string>
#include <utility>

namespace rptp::runtime {
namespace {

constexpr std::uint32_t kOpcodeAddiu = 0x09U;
constexpr std::uint32_t kOpcodeSlti = 0x0AU;
constexpr std::uint32_t kOpcodeSltiu = 0x0BU;
constexpr std::uint32_t kOpcodeAndi = 0x0CU;
constexpr std::uint32_t kOpcodeOri = 0x0DU;
constexpr std::uint32_t kOpcodeXori = 0x0EU;
constexpr std::uint32_t kOpcodeLui = 0x0FU;
constexpr std::uint32_t kOpcodeDaddiu = 0x19U;
constexpr std::uint32_t kOpcodeLw = 0x23U;
constexpr std::uint32_t kOpcodeSw = 0x2BU;
constexpr std::uint32_t kOpcodeBeq = 0x04U;
constexpr std::uint32_t kOpcodeBne = 0x05U;
constexpr std::uint32_t kOpcodeJ = 0x02U;
constexpr std::uint32_t kOpcodeJal = 0x03U;
constexpr std::uint32_t kFunctSll = 0x00U;
constexpr std::uint32_t kFunctJr = 0x08U;
constexpr std::uint32_t kFunctAddu = 0x21U;
constexpr std::uint32_t kFunctAnd = 0x24U;
constexpr std::uint32_t kFunctOr = 0x25U;
constexpr std::uint32_t kFunctXor = 0x26U;
constexpr std::uint32_t kFunctNor = 0x27U;
constexpr std::uint32_t kFunctSlt = 0x2AU;
constexpr std::uint32_t kFunctSltu = 0x2BU;

enum class Op {
  Nop,
  Addiu,
  Addu,
  Slti,
  Sltiu,
  Daddiu,
  Andi,
  Ori,
  Xori,
  Lui,
  And,
  Or,
  Xor,
  Nor,
  Slt,
  Sltu,
  Sll,
  Lw,
  Sw,
  Beq,
  Bne,
  J,
  Jal,
  Jr,
};

struct Instruction {
  Op op = Op::Nop;
  std::uint32_t rs = 0;
  std::uint32_t rt = 0;
  std::uint32_t rd = 0;
  std::uint32_t shamt = 0;
  std::uint32_t immediate = 0;
  std::uint32_t target = 0;
};

ExecOutcome fail(ExecErrorCode code, std::string message) {
  ExecOutcome outcome;
  outcome.error = ExecError{code, std::move(message)};
  return outcome;
}

std::string address_message(const char* what, std::uint32_t address) {
  char buffer[96] = {};
  std::snprintf(buffer, sizeof(buffer), "%s at 0x%08x", what, static_cast<unsigned>(address));
  return buffer;
}

std::string instruction_message(std::uint32_t word, std::uint32_t pc) {
  char buffer[128] = {};
  std::snprintf(buffer, sizeof(buffer), "unsupported instruction 0x%08x at 0x%08x",
                static_cast<unsigned>(word), static_cast<unsigned>(pc));
  return buffer;
}

std::uint32_t sign_extend_16(std::uint32_t value) {
  return (value & 0x8000U) != 0 ? (value | 0xFFFF0000U) : value;
}

std::uint64_t sign_extend_32(std::uint32_t value) {
  return (value & 0x80000000U) != 0
             ? (static_cast<std::uint64_t>(value) | 0xFFFFFFFF00000000ULL)
             : static_cast<std::uint64_t>(value);
}

std::uint32_t read_le32(const std::uint8_t* bytes) {
  return static_cast<std::uint32_t>(bytes[0]) | (static_cast<std::uint32_t>(bytes[1]) << 8U) |
         (static_cast<std::uint32_t>(bytes[2]) << 16U) | (static_cast<std::uint32_t>(bytes[3]) << 24U);
}

std::array<std::uint8_t, 4> write_le32(std::uint32_t value) {
  return {static_cast<std::uint8_t>(value & 0xFFU), static_cast<std::uint8_t>((value >> 8U) & 0xFFU),
          static_cast<std::uint8_t>((value >> 16U) & 0xFFU),
          static_cast<std::uint8_t>((value >> 24U) & 0xFFU)};
}

const LoadedSegment* find_segment(const LoadReport& report, std::uint32_t address) {
  for (const LoadedSegment& segment : report.segments) {
    const std::uint64_t end =
        static_cast<std::uint64_t>(segment.virtual_address) + static_cast<std::uint64_t>(segment.memory_size);
    if (static_cast<std::uint64_t>(address) >= segment.virtual_address &&
        static_cast<std::uint64_t>(address) < end) {
      return &segment;
    }
  }
  return nullptr;
}

std::uint32_t branch_target(std::uint32_t pc, std::uint32_t immediate) {
  const std::uint64_t sum = static_cast<std::uint64_t>(pc) + 4U + (static_cast<std::uint64_t>(immediate) << 2U);
  return static_cast<std::uint32_t>(sum & 0xFFFFFFFFULL);
}

std::uint32_t jump_target(std::uint32_t pc, std::uint32_t word) {
  return ((pc + 4U) & 0xF0000000U) | ((word & 0x03FFFFFFU) << 2U);
}

bool decode(std::uint32_t word, std::uint32_t pc, Instruction& instruction) {
  if (word == 0) {
    instruction.op = Op::Nop;
    return true;
  }
  const std::uint32_t opcode = word >> 26U;
  const std::uint32_t rs = (word >> 21U) & 0x1FU;
  const std::uint32_t rt = (word >> 16U) & 0x1FU;
  const std::uint32_t rd = (word >> 11U) & 0x1FU;
  const std::uint32_t shamt = (word >> 6U) & 0x1FU;
  const std::uint32_t funct = word & 0x3FU;
  const std::uint32_t sign_immediate = sign_extend_16(word & 0xFFFFU);
  const std::uint32_t zero_immediate = word & 0xFFFFU;
  switch (opcode) {
    case kOpcodeAddiu:
      instruction = {Op::Addiu, rs, rt, 0, 0, sign_immediate, 0};
      return true;
    case kOpcodeSlti:
      instruction = {Op::Slti, rs, rt, 0, 0, sign_immediate, 0};
      return true;
    case kOpcodeSltiu:
      instruction = {Op::Sltiu, rs, rt, 0, 0, sign_immediate, 0};
      return true;
    case kOpcodeAndi:
      instruction = {Op::Andi, rs, rt, 0, 0, zero_immediate, 0};
      return true;
    case kOpcodeOri:
      instruction = {Op::Ori, rs, rt, 0, 0, zero_immediate, 0};
      return true;
    case kOpcodeXori:
      instruction = {Op::Xori, rs, rt, 0, 0, zero_immediate, 0};
      return true;
    case kOpcodeLui:
      if (rs != 0) {
        return false;
      }
      instruction = {Op::Lui, rs, rt, 0, 0, zero_immediate, 0};
      return true;
    case kOpcodeDaddiu:
      instruction = {Op::Daddiu, rs, rt, 0, 0, sign_immediate, 0};
      return true;
    case kOpcodeLw:
      instruction = {Op::Lw, rs, rt, 0, 0, sign_immediate, 0};
      return true;
    case kOpcodeSw:
      instruction = {Op::Sw, rs, rt, 0, 0, sign_immediate, 0};
      return true;
    case kOpcodeBeq:
      instruction = {Op::Beq, rs, rt, 0, 0, sign_immediate, branch_target(pc, sign_immediate)};
      return true;
    case kOpcodeBne:
      instruction = {Op::Bne, rs, rt, 0, 0, sign_immediate, branch_target(pc, sign_immediate)};
      return true;
    case kOpcodeJ:
      instruction = {Op::J, 0, 0, 0, 0, 0, jump_target(pc, word)};
      return true;
    case kOpcodeJal:
      instruction = {Op::Jal, 0, 0, 0, 0, 0, jump_target(pc, word)};
      return true;
    case 0:
      if (funct == kFunctAddu && shamt == 0) {
        instruction = {Op::Addu, rs, rt, rd, 0, 0, 0};
        return true;
      }
      if ((funct == kFunctAnd || funct == kFunctOr || funct == kFunctXor || funct == kFunctNor) &&
          shamt == 0) {
        const Op op = funct == kFunctAnd   ? Op::And
                      : funct == kFunctOr  ? Op::Or
                      : funct == kFunctXor ? Op::Xor
                                           : Op::Nor;
        instruction = {op, rs, rt, rd, 0, 0, 0};
        return true;
      }
      if (funct == kFunctSlt && shamt == 0) {
        instruction = {Op::Slt, rs, rt, rd, 0, 0, 0};
        return true;
      }
      if (funct == kFunctSltu && shamt == 0) {
        instruction = {Op::Sltu, rs, rt, rd, 0, 0, 0};
        return true;
      }
      if (funct == kFunctJr && rt == 0 && rd == 0 && shamt == 0) {
        instruction = {Op::Jr, rs, 0, 0, 0, 0, 0};
        return true;
      }
      if (funct == kFunctSll) {
        if (rs != 0) {
          return false;
        }
        instruction = {Op::Sll, rs, rt, rd, shamt, 0, 0};
        return true;
      }
      return false;
    default:
      return false;
  }
}

bool is_control(Op op) {
  return op == Op::Beq || op == Op::Bne || op == Op::J || op == Op::Jal || op == Op::Jr;
}

}  // namespace

std::string_view to_string(ExecErrorCode code) {
  switch (code) {
    case ExecErrorCode::EntryUnaligned:
      return "EXEC_ENTRY_UNALIGNED";
    case ExecErrorCode::PcUnaligned:
      return "EXEC_PC_UNALIGNED";
    case ExecErrorCode::UnsupportedInstruction:
      return "EXEC_UNSUPPORTED_INSTRUCTION";
    case ExecErrorCode::PcNotExecutable:
      return "EXEC_PC_NOT_EXECUTABLE";
    case ExecErrorCode::FetchFault:
      return "EXEC_FETCH_FAULT";
    case ExecErrorCode::MemoryFault:
      return "EXEC_MEMORY_FAULT";
    case ExecErrorCode::DelaySlotControl:
      return "EXEC_DELAY_SLOT_CONTROL";
    case ExecErrorCode::DelaySlotMissing:
      return "EXEC_DELAY_SLOT_MISSING";
    case ExecErrorCode::StepLimit:
      return "EXEC_STEP_LIMIT";
    case ExecErrorCode::Internal:
      return "EXEC_INTERNAL";
  }
  return "EXEC_INTERNAL";
}

std::string_view to_string(HaltReason reason) {
  switch (reason) {
    case HaltReason::UnmappedPc:
      return "unmapped-pc";
  }
  return "unmapped-pc";
}

bool ExecOutcome::ok() const noexcept {
  return !error.has_value();
}

ExecOutcome execute_loaded(const LoadReport& report, GuestMemory& memory, const ExecOptions& options) {
  if (options.max_steps == 0) {
    return fail(ExecErrorCode::Internal, "step budget must be positive");
  }
  if ((report.entry_point & 3U) != 0) {
    return fail(ExecErrorCode::EntryUnaligned,
                address_message("unaligned entry point", report.entry_point));
  }

  ExecResult result;
  result.entry_point = report.entry_point;
  std::array<std::uint64_t, 32>& registers = result.registers;
  std::map<std::uint32_t, std::uint32_t> writes;
  std::uint32_t pc = report.entry_point;
  std::optional<std::uint32_t> pending_target;

  while (true) {
    const LoadedSegment* segment = find_segment(report, pc);
    if (segment == nullptr) {
      if (pending_target.has_value()) {
        return fail(ExecErrorCode::DelaySlotMissing,
                    address_message("missing delay-slot instruction", pc));
      }
      result.final_pc = pc;
      result.halt_reason = HaltReason::UnmappedPc;
      result.memory_writes.reserve(writes.size());
      for (const auto& [address, value] : writes) {
        result.memory_writes.push_back(MemoryWrite{address, value});
      }
      return ExecOutcome{std::nullopt, std::move(result)};
    }
    if (!segment->executable()) {
      return fail(pending_target.has_value() ? ExecErrorCode::DelaySlotMissing
                                             : ExecErrorCode::PcNotExecutable,
                  address_message(pending_target.has_value() ? "non-executable delay-slot PC"
                                                             : "PC outside executable segments",
                                  pc));
    }
    if ((pc & 3U) != 0) {
      return fail(pending_target.has_value() ? ExecErrorCode::DelaySlotMissing : ExecErrorCode::PcUnaligned,
                  address_message("unaligned PC", pc));
    }
    if (result.steps >= options.max_steps) {
      char buffer[96] = {};
      std::snprintf(buffer, sizeof(buffer), "step limit %zu reached at 0x%08x", options.max_steps,
                    static_cast<unsigned>(pc));
      return fail(ExecErrorCode::StepLimit, buffer);
    }
    const std::span<const std::uint8_t> view = memory.view(pc, 4);
    if (view.empty()) {
      return fail(pending_target.has_value() ? ExecErrorCode::DelaySlotMissing : ExecErrorCode::FetchFault,
                  address_message("instruction fetch outside a mapped region", pc));
    }
    const std::uint32_t word = read_le32(view.data());
    Instruction instruction;
    if (!decode(word, pc, instruction)) {
      return fail(ExecErrorCode::UnsupportedInstruction, instruction_message(word, pc));
    }
    if (pending_target.has_value() && is_control(instruction.op)) {
      return fail(ExecErrorCode::DelaySlotControl,
                  address_message("control transfer in a delay slot", pc));
    }
    if (options.trace) {
      result.trace.push_back(pc);
    }
    ++result.steps;

    std::optional<std::uint32_t> new_target;
    const auto write_register = [&registers](std::uint32_t index, std::uint64_t value) {
      if (index != 0) {
        registers[index] = value;
      }
    };
    switch (instruction.op) {
      case Op::Nop:
        break;
      case Op::Addiu: {
        const auto sum = static_cast<std::uint32_t>(static_cast<std::uint32_t>(registers[instruction.rs]) +
                                                    instruction.immediate);
        write_register(instruction.rt, sign_extend_32(sum));
        break;
      }
      case Op::Addu: {
        const auto sum = static_cast<std::uint32_t>(static_cast<std::uint32_t>(registers[instruction.rs]) +
                                                    static_cast<std::uint32_t>(registers[instruction.rt]));
        write_register(instruction.rd, sign_extend_32(sum));
        break;
      }
      case Op::Slti: {
        const bool less = static_cast<std::int64_t>(registers[instruction.rs]) <
                          static_cast<std::int64_t>(sign_extend_32(instruction.immediate));
        write_register(instruction.rt, less ? 1U : 0U);
        break;
      }
      case Op::Sltiu: {
        const bool less = registers[instruction.rs] < sign_extend_32(instruction.immediate);
        write_register(instruction.rt, less ? 1U : 0U);
        break;
      }
      case Op::Daddiu:
        write_register(instruction.rt, registers[instruction.rs] + sign_extend_32(instruction.immediate));
        break;
      case Op::Andi:
        write_register(instruction.rt, (registers[instruction.rs] & 0xFFFFFFFFULL) &
                                           static_cast<std::uint64_t>(instruction.immediate));
        break;
      case Op::Ori:
        write_register(instruction.rt, registers[instruction.rs] |
                                           static_cast<std::uint64_t>(instruction.immediate));
        break;
      case Op::Xori:
        write_register(instruction.rt, registers[instruction.rs] ^
                                           static_cast<std::uint64_t>(instruction.immediate));
        break;
      case Op::Lui:
        write_register(instruction.rt, sign_extend_32((instruction.immediate << 16U) & 0xFFFFFFFFU));
        break;
      case Op::And:
        write_register(instruction.rd, registers[instruction.rs] & registers[instruction.rt]);
        break;
      case Op::Or:
        write_register(instruction.rd, registers[instruction.rs] | registers[instruction.rt]);
        break;
      case Op::Xor:
        write_register(instruction.rd, registers[instruction.rs] ^ registers[instruction.rt]);
        break;
      case Op::Nor:
        write_register(instruction.rd, ~(registers[instruction.rs] | registers[instruction.rt]));
        break;
      case Op::Slt: {
        const bool less = static_cast<std::int64_t>(registers[instruction.rs]) <
                          static_cast<std::int64_t>(registers[instruction.rt]);
        write_register(instruction.rd, less ? 1U : 0U);
        break;
      }
      case Op::Sltu: {
        const bool less = registers[instruction.rs] < registers[instruction.rt];
        write_register(instruction.rd, less ? 1U : 0U);
        break;
      }
      case Op::Sll: {
        const auto value = static_cast<std::uint32_t>(static_cast<std::uint32_t>(registers[instruction.rt])
                                                      << instruction.shamt);
        write_register(instruction.rd, sign_extend_32(value));
        break;
      }
      case Op::Lw: {
        const auto address = static_cast<std::uint32_t>(static_cast<std::uint32_t>(registers[instruction.rs]) +
                                                        instruction.immediate);
        std::array<std::uint8_t, 4> bytes{};
        if (!memory.read(address, bytes)) {
          return fail(ExecErrorCode::MemoryFault, address_message("load outside mapped memory", address));
        }
        write_register(instruction.rt, sign_extend_32(read_le32(bytes.data())));
        break;
      }
      case Op::Sw: {
        const auto address = static_cast<std::uint32_t>(static_cast<std::uint32_t>(registers[instruction.rs]) +
                                                        instruction.immediate);
        const auto value = static_cast<std::uint32_t>(registers[instruction.rt]);
        const std::array<std::uint8_t, 4> bytes = write_le32(value);
        if (!memory.write(address, bytes)) {
          return fail(ExecErrorCode::MemoryFault, address_message("store outside mapped memory", address));
        }
        writes[address] = value;
        break;
      }
      case Op::Beq:
        new_target = registers[instruction.rs] == registers[instruction.rt] ? instruction.target
                                                                            : (pc + 8U) & 0xFFFFFFFFU;
        break;
      case Op::Bne:
        new_target = registers[instruction.rs] != registers[instruction.rt] ? instruction.target
                                                                            : (pc + 8U) & 0xFFFFFFFFU;
        break;
      case Op::J:
        new_target = instruction.target;
        break;
      case Op::Jal:
        registers[31] = (pc + 8U) & 0xFFFFFFFFU;
        new_target = instruction.target;
        break;
      case Op::Jr:
        new_target = static_cast<std::uint32_t>(registers[instruction.rs]);
        break;
    }
    registers[0] = 0;

    if (pending_target.has_value()) {
      pc = *pending_target;
      pending_target.reset();
    } else if (new_target.has_value()) {
      pc = (pc + 4U) & 0xFFFFFFFFU;
      pending_target = *new_target;
    } else {
      pc = (pc + 4U) & 0xFFFFFFFFU;
    }
  }
}

}  // namespace rptp::runtime
