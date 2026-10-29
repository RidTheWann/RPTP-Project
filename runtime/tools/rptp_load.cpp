// SPDX-License-Identifier: GPL-3.0-or-later
#include <charconv>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <limits>
#include <span>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

#include "rptp/runtime/elf_loader.hpp"

namespace {

using rptp::runtime::LoadError;
using rptp::runtime::LoadLimits;
using rptp::runtime::LoadReport;
using rptp::runtime::to_string;

struct Options {
  bool json = false;
  LoadLimits limits;
  std::string input;
};

void print_usage(std::ostream& out) {
  out << "usage: rptp-load [--json] [--max-image-bytes N] [--max-guest-bytes N] <elf>\n"
      << "\n"
      << "Validates an ELF32 little-endian EM_MIPS executable and reports its PT_LOAD map.\n"
      << "The input is read-only. No instruction executes and no file is written.\n";
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

std::string render_success(const LoadReport& report, std::size_t image_bytes) {
  std::ostringstream out;
  out << "{\"schema\":\"rptp.runtime.load.v1\",\"status\":\"ok\""
      << ",\"image_bytes\":" << image_bytes
      << ",\"entry_point\":\"" << hex32(report.entry_point) << "\""
      << ",\"load_segment_count\":" << report.segments.size()
      << ",\"total_file_bytes\":" << report.total_file_bytes
      << ",\"total_memory_bytes\":" << report.total_memory_bytes
      << ",\"segments\":[";
  for (std::size_t index = 0; index < report.segments.size(); ++index) {
    if (index != 0) {
      out << ',';
    }
    const auto& segment = report.segments[index];
    out << "{\"program_header_index\":" << segment.program_header_index
        << ",\"virtual_address\":\"" << hex32(segment.virtual_address) << "\""
        << ",\"file_offset\":" << segment.file_offset
        << ",\"file_size\":" << segment.file_size
        << ",\"memory_size\":" << segment.memory_size
        << ",\"flags\":" << segment.flags
        << ",\"executable\":" << (segment.executable() ? "true" : "false")
        << ",\"writable\":" << (segment.writable() ? "true" : "false")
        << ",\"alignment\":" << segment.alignment
        << '}';
  }
  out << "]}";
  return out.str();
}

std::string render_error(const LoadError& error) {
  std::ostringstream out;
  out << "{\"schema\":\"rptp.runtime.load.v1\",\"status\":\"error\""
      << ",\"error\":{\"code\":\"" << to_string(error.code) << "\",\"message\":\"" << error.message << "\"}}";
  return out.str();
}

}  // namespace

int main(int argc, char** argv) {
  Options options;
  for (int index = 1; index < argc; ++index) {
    const std::string_view argument = argv[index];
    if (argument == "--json") {
      options.json = true;
    } else if (argument == "--help" || argument == "-h") {
      print_usage(std::cout);
      return 0;
    } else if (argument == "--max-image-bytes" || argument == "--max-guest-bytes") {
      if (index + 1 >= argc) {
        std::cerr << "rptp-load: missing value for " << argument << '\n';
        print_usage(std::cerr);
        return 1;
      }
      const std::string_view text = argv[++index];
      std::size_t value = 0;
      if (!parse_positive_size(text, value)) {
        std::cerr << "rptp-load: invalid positive byte limit: " << text << '\n';
        return 1;
      }
      if (argument == "--max-image-bytes") {
        options.limits.max_image_bytes = value;
      } else {
        options.limits.max_guest_bytes = value;
      }
    } else if (!argument.empty() && argument.front() == '-') {
      std::cerr << "rptp-load: unknown option: " << argument << '\n';
      print_usage(std::cerr);
      return 1;
    } else if (!options.input.empty()) {
      std::cerr << "rptp-load: more than one input file was provided\n";
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
    std::cerr << "rptp-load: cannot read input file\n";
    return 1;
  }

  const auto outcome = rptp::runtime::load_elf(image, options.limits);
  if (!outcome.ok()) {
    if (options.json) {
      std::cout << render_error(*outcome.error) << '\n';
    } else {
      std::cerr << "rptp-load: " << to_string(outcome.error->code) << ": " << outcome.error->message << '\n';
    }
    return 2;
  }
  if (options.json) {
    std::cout << render_success(outcome.report, image.size()) << '\n';
  } else {
    std::cout << "loaded " << outcome.report.segments.size() << " PT_LOAD segment(s); entry "
              << hex32(outcome.report.entry_point) << "; file bytes " << outcome.report.total_file_bytes
              << "; memory bytes " << outcome.report.total_memory_bytes << '\n';
  }
  return 0;
}
