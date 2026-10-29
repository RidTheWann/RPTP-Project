// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef RPTP_RUNTIME_GUEST_MEMORY_HPP
#define RPTP_RUNTIME_GUEST_MEMORY_HPP

#include <cstddef>
#include <cstdint>
#include <map>
#include <span>
#include <vector>

namespace rptp::runtime {

inline constexpr std::size_t kDefaultMaxGuestBytes = 64U * 1024U * 1024U;
inline constexpr std::uint64_t kGuestAddressSpaceSize = std::uint64_t{1} << 32;

// Sparse page-agnostic guest memory. A mapped range must fit entirely inside
// one region; reads and writes never span region boundaries.
class GuestMemory {
 public:
  explicit GuestMemory(std::size_t max_bytes = kDefaultMaxGuestBytes);
  GuestMemory(const GuestMemory&) = delete;
  GuestMemory& operator=(const GuestMemory&) = delete;
  GuestMemory(GuestMemory&&) noexcept = default;
  GuestMemory& operator=(GuestMemory&&) noexcept = default;

  [[nodiscard]] bool map(std::uint32_t address, std::size_t size, std::span<const std::uint8_t> initial);
  [[nodiscard]] bool write(std::uint32_t address, std::span<const std::uint8_t> bytes);
  [[nodiscard]] bool read(std::uint32_t address, std::span<std::uint8_t> out) const;
  [[nodiscard]] std::span<const std::uint8_t> view(std::uint32_t address, std::size_t size) const;
  [[nodiscard]] bool is_mapped(std::uint32_t address, std::size_t size) const;
  [[nodiscard]] std::size_t mapped_bytes() const noexcept;
  [[nodiscard]] std::size_t region_count() const noexcept;
  [[nodiscard]] std::size_t max_bytes() const noexcept;

 private:
  std::map<std::uint32_t, std::vector<std::uint8_t>> regions_;
  std::size_t mapped_bytes_ = 0;
  std::size_t max_bytes_;
};

}  // namespace rptp::runtime

#endif
