// SPDX-License-Identifier: GPL-3.0-or-later
#include "rptp/runtime/guest_memory.hpp"

#include <algorithm>
#include <cstdint>
#include <utility>

namespace rptp::runtime {
namespace {

bool checked_end(std::uint32_t address, std::size_t size, std::uint64_t& end) {
  const std::uint64_t limit = kGuestAddressSpaceSize - static_cast<std::uint64_t>(address);
  if (static_cast<std::uint64_t>(size) > limit) {
    return false;
  }
  end = static_cast<std::uint64_t>(address) + static_cast<std::uint64_t>(size);
  return true;
}

bool overlaps(const std::map<std::uint32_t, std::vector<std::uint8_t>>& regions, std::uint32_t address,
              std::uint64_t end) {
  auto next = regions.lower_bound(address);
  if (next != regions.end() && static_cast<std::uint64_t>(next->first) < end) {
    return true;
  }
  if (next != regions.begin()) {
    --next;
    const std::uint64_t previous_end = static_cast<std::uint64_t>(next->first) + next->second.size();
    if (previous_end > static_cast<std::uint64_t>(address)) {
      return true;
    }
  }
  return false;
}

}  // namespace

GuestMemory::GuestMemory(std::size_t max_bytes) : max_bytes_(max_bytes) {}

bool GuestMemory::map(std::uint32_t address, std::size_t size, std::span<const std::uint8_t> initial) {
  std::uint64_t end = 0;
  if (size == 0 || initial.size() > size || !checked_end(address, size, end)) {
    return false;
  }
  if (mapped_bytes_ > max_bytes_ || size > max_bytes_ - mapped_bytes_) {
    return false;
  }
  if (overlaps(regions_, address, end)) {
    return false;
  }
  std::vector<std::uint8_t> bytes(size, 0);
  std::copy(initial.begin(), initial.end(), bytes.begin());
  regions_.emplace(address, std::move(bytes));
  mapped_bytes_ += size;
  return true;
}

bool GuestMemory::write(std::uint32_t address, std::span<const std::uint8_t> bytes) {
  if (bytes.empty()) {
    return true;
  }
  std::uint64_t end = 0;
  if (!checked_end(address, bytes.size(), end)) {
    return false;
  }
  auto region = regions_.upper_bound(address);
  if (region == regions_.begin()) {
    return false;
  }
  --region;
  const std::uint64_t region_end = static_cast<std::uint64_t>(region->first) + region->second.size();
  if (end > region_end) {
    return false;
  }
  const auto offset = static_cast<std::size_t>(address - region->first);
  std::copy(bytes.begin(), bytes.end(), region->second.begin() + static_cast<std::ptrdiff_t>(offset));
  return true;
}

bool GuestMemory::read(std::uint32_t address, std::span<std::uint8_t> out) const {
  if (out.empty()) {
    return true;
  }
  std::uint64_t end = 0;
  if (!checked_end(address, out.size(), end)) {
    return false;
  }
  auto region = regions_.upper_bound(address);
  if (region == regions_.begin()) {
    return false;
  }
  --region;
  const std::uint64_t region_end = static_cast<std::uint64_t>(region->first) + region->second.size();
  if (end > region_end) {
    return false;
  }
  const auto offset = static_cast<std::size_t>(address - region->first);
  std::copy(region->second.begin() + static_cast<std::ptrdiff_t>(offset),
            region->second.begin() + static_cast<std::ptrdiff_t>(offset + out.size()), out.begin());
  return true;
}

std::span<const std::uint8_t> GuestMemory::view(std::uint32_t address, std::size_t size) const {
  if (size == 0) {
    return {};
  }
  std::uint64_t end = 0;
  if (!checked_end(address, size, end)) {
    return {};
  }
  auto region = regions_.upper_bound(address);
  if (region == regions_.begin()) {
    return {};
  }
  --region;
  const std::uint64_t region_end = static_cast<std::uint64_t>(region->first) + region->second.size();
  if (end > region_end) {
    return {};
  }
  const auto offset = static_cast<std::size_t>(address - region->first);
  return std::span<const std::uint8_t>(region->second.data() + offset, size);
}

bool GuestMemory::is_mapped(std::uint32_t address, std::size_t size) const {
  return !view(address, size).empty();
}

std::size_t GuestMemory::mapped_bytes() const noexcept {
  return mapped_bytes_;
}

std::size_t GuestMemory::region_count() const noexcept {
  return regions_.size();
}

std::size_t GuestMemory::max_bytes() const noexcept {
  return max_bytes_;
}

}  // namespace rptp::runtime
