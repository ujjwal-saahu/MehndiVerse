/// Mirrors the backend's `AvailableSlotOut`/`AvailableSlotsOut` (see
/// app/schemas/scheduling.py) — see docs/artist-scheduling.md. Only the
/// customer-facing read-only slot shape is modeled here; the artist-side
/// self-service scheduling management (settings/rules/blocks/calendar) is
/// web-only in this phase — see docs/artist-scheduling.md#client-implementations.
class AvailableSlotData {
  const AvailableSlotData({required this.start, required this.end});

  final DateTime start;
  final DateTime end;

  factory AvailableSlotData.fromJson(Map<String, dynamic> json) {
    return AvailableSlotData(
      start: DateTime.parse(json['start'] as String),
      end: DateTime.parse(json['end'] as String),
    );
  }
}

class AvailableSlotsData {
  const AvailableSlotsData({
    required this.artistProfileId,
    required this.serviceId,
    required this.artistTimezone,
    required this.slots,
  });

  final String artistProfileId;
  final String serviceId;
  final String artistTimezone;
  final List<AvailableSlotData> slots;

  factory AvailableSlotsData.fromJson(Map<String, dynamic> json) {
    return AvailableSlotsData(
      artistProfileId: json['artist_profile_id'] as String,
      serviceId: json['service_id'] as String,
      artistTimezone: json['artist_timezone'] as String,
      slots: (json['slots'] as List<dynamic>)
          .map((entry) => AvailableSlotData.fromJson(entry as Map<String, dynamic>))
          .toList(),
    );
  }
}
