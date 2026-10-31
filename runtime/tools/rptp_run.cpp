// SPDX-License-Identifier: GPL-3.0-or-later
#include <charconv>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

#include "rptp/runtime/elf_loader.hpp"
#include "rptp/runtime/execution.hpp"

namespace {

using rptp::runtime::ExecOptions;
using rptp::runtime::ExecOutcome;
using rptp::runtime::ExecResult;
using rptp::runtime::LoadError;
using rptp::runtime::LoadLimits;
using rptp::runtime::LoadOutcome;
using rptp::runtime::to_string;

struct Options {
  bool json = false;
  bool trace = false;
  LoadLimits limits;
  ExecOptions exec;
  std::string input;
};

void print_usage(std::ostream& out) {
  out << "usage: rptp-run [--json] [--trace] [--max-steps N] [--max-image-bytes N] [--max-guest-bytes N] <elf>\n"
      << "\n"
      << "Loads an ELF32 little-endian EM_MIPS executable and executes the accepted\n"
      << "synthetic instruction subset until the next PC leaves every loaded segment.\n"
      << "No kernel, syscall, device, boot or compatibility behavior is provided.\n";
}

bool parse_positive_size(std::string_view text, std::size_t& value) {
  if (text.empty()) {
    return false;
  }
  std::uint64_t parsed = 0;
  const auto result = std::from_chars(text.data(), text.data() + text.size(), parsed);
  if (result.ec != std::errc{} || result.ptr != text.data() + text.size() || parsed == 0) {
    return false;
  }
  if (parsed > std::numeric_limits<std::size_t>::max()) {
    return false;
  }
  value = static_cast<std::size_t>(parsed);
  return true;
}

bool read_file(const std::string& path, std::vector<std::uint8_t>& data) {
  std::ifstream input(path, std::ios::binary | std::ios::ate);
  if (!input) {
    return false;
  }
  const std::streampos end = input.tellg();
  if (end < 0) {
    return false;
  }
  const auto size = static_cast<std::size_t>(end);
  data.resize(size);
  input.seekg(0, std::ios::beg);
  if (size != 0) {
    input.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(size));
    if (!input || static_cast<std::size_t>(input.gcount()) != size) {
      return false;
    }
  }
  return true;
}

std::string hex32(std::uint32_t value) {
  char buffer[11] = {};
  std::snprintf(buffer, sizeof(buffer), "0x%08x", static_cast<unsigned>(value));
  return buffer;
}

std::string hex64(std::uint64_t value) {
  char buffer[19] = {};
  std::snprintf(buffer, sizeof(buffer), "0x%016llx", static_cast<unsigned long long>(value));
  return buffer;
}

std::string render_success(const ExecResult& result, std::size_t image_bytes) {
  std::ostringstream out;
  out << "{\"schema\":\"rptp.runtime.run.v1\",\"status\":\"ok\""
      << ",\"image_bytes\":" << image_bytes
      << ",\"entry_point\":\"" << hex32(result.entry_point) << "\""
      << ",\"steps\":" << result.steps
      << ",\"halt_reason\":\"" << to_string(result.halt_reason) << "\""
      << ",\"final_pc\":\"" << hex32(result.final_pc) << "\""
      << ",\"hi\":\"" << hex64(result.hi) << "\""
      << ",\"lo\":\"" << hex64(result.lo) << "\""
      << ",\"registers\":[";
  for (std::size_t index = 0; index < result.registers.size(); ++index) {
    if (index != 0) {
      out << ',';
    }
    out << '"' << hex64(result.registers[index]) << '"';
  }
  out << "],\"fpr\":[";
  for (std::size_t index = 0; index < result.fpr.size(); ++index) {
    if (index != 0) {
      out << ',';
    }
    out << '"' << hex32(result.fpr[index]) << '"';
  }
  out << "],\"memory_writes\":[";
  for (std::size_t index = 0; index < result.memory_writes.size(); ++index) {
    if (index != 0) {
      out << ',';
    }
    out << "{\"address\":\"" << hex32(result.memory_writes[index].address) << "\""
        << ",\"value\":\"" << hex32(result.memory_writes[index].value) << "\""
        << ",\"width\":" << static_cast<unsigned>(result.memory_writes[index].width) << "}";
  }
  out << "],\"trace\":[";
  for (std::size_t index = 0; index < result.trace.size(); ++index) {
    if (index != 0) {
      out << ',';
    }
    out << '"' << hex32(result.trace[index]) << '"';
  }
  out << "]}";
  return out.str();
}

std::string render_error(std::string_view code, const std::string& message) {
  std::ostringstream out;
  out << "{\"schema\":\"rptp.runtime.run.v1\",\"status\":\"error\""
      << ",\"error\":{\"code\":\"" << code << "\",\"message\":\"" << message << "\"}}";
  return out.str();
}

}  // namespace

int main(int argc, char** argv) {
  Options options;
  for (int index = 1; index < argc; ++index) {
    const std::string_view argument = argv[index];
    if (argument == "--json") {
      options.json = true;
    } else if (argument == "--trace") {
      options.trace = true;
    } else if (argument == "--help" || argument == "-h") {
      print_usage(std::cout);
      return 0;
    } else if (argument == "--max-steps" || argument == "--max-image-bytes" ||
               argument == "--max-guest-bytes") {
      if (index + 1 >= argc) {
        std::cerr << "rptp-run: missing value for " << argument << '\n';
        print_usage(std::cerr);
        return 1;
      }
      const std::string_view text = argv[++index];
      std::size_t value = 0;
      if (!parse_positive_size(text, value)) {
        std::cerr << "rptp-run: invalid positive limit: " << text << '\n';
        return 1;
      }
      if (argument == "--max-steps") {
        options.exec.max_steps = value;
      } else if (argument == "--max-image-bytes") {
        options.limits.max_image_bytes = value;
      } else {
        options.limits.max_guest_bytes = value;
      }
    } else if (!argument.empty() && argument.front() == '-') {
      std::cerr << "rptp-run: unknown option: " << argument << '\n';
      print_usage(std::cerr);
      return 1;
    } else if (!options.input.empty()) {
      std::cerr << "rptp-run: more than one input file was provided\n";
      return 1;
    } else {
      options.input = std::string(argument);
    }
  }
  if (options.input.empty()) {
    print_usage(std::cerr);
    return 1;
  }

  std::vector<std::uint8_t> image;
  if (!read_file(options.input, image)) {
    std::cerr << "rptp-run: cannot read input file\n";
    return 1;
  }

  LoadOutcome loaded = rptp::runtime::load_elf(image, options.limits);
  if (!loaded.ok()) {
    if (options.json) {
      std::cout << render_error(to_string(loaded.error->code), loaded.error->message) << '\n';
    } else {
      std::cerr << "rptp-run: " << to_string(loaded.error->code) << ": " << loaded.error->message << '\n';
    }
    return 2;
  }

  options.exec.trace = options.trace;
  const ExecOutcome executed = rptp::runtime::execute_loaded(loaded.report, loaded.memory, options.exec);
  if (!executed.ok()) {
    if (options.json) {
      std::cout << render_error(to_string(executed.error->code), executed.error->message) << '\n';
    } else {
      std::cerr << "rptp-run: " << to_string(executed.error->code) << ": " << executed.error->message
                << '\n';
    }
    return 2;
  }
  if (options.json) {
    std::cout << render_success(executed.result, image.size()) << '\n';
  } else {
    std::cout << "executed " << executed.result.steps << " step(s); halt "
              << to_string(executed.result.halt_reason) << "; final pc "
              << hex32(executed.result.final_pc) << '\n';
  }
  return 0;
}
