/// Mirrors the backend's booking schemas (see app/schemas/booking.py) — see
/// docs/booking-lifecycle.md. Only the customer-facing surface is modeled
/// here (draft/submit/detail/cancel/reschedule/quote decisions); the
/// artist-side inbox/review/quote-sending screens are web-only in this
/// phase — see docs/booking-lifecycle.md#7-client-implementations, the same
/// scope decision Phases 10-12 made for artist self-service management.
library;

const Map<String, String> bookingStatusLabels = {
  'draft': 'Draft',
  'requested': 'Requested',
  'artist_reviewing': 'Artist reviewing',
  'quotation_sent': 'Quote sent',
  'customer_reviewing': 'Reviewing quote',
  'confirmed': 'Confirmed',
  'deposit_pending': 'Deposit pending',
  'deposit_paid': 'Deposit paid',
  'in_progress': 'In progress',
  'completed': 'Completed',
  'cancelled': 'Cancelled',
  'rejected': 'Rejected',
  'refund_requested': 'Refund requested',
  'refunded': 'Refunded',
  'disputed': 'Disputed',
};

const Map<String, String> eventTypeLabels = {
  'wedding': 'Wedding',
  'engagement': 'Engagement',
  'festival': 'Festival',
  'baby_shower': 'Baby shower',
  'party': 'Party',
  'corporate_event': 'Corporate event',
  'other': 'Other',
};

class BookingQuoteData {
  const BookingQuoteData({
    required this.id,
    required this.amount,
    required this.currency,
    required this.terms,
    required this.status,
  });

  final String id;
  final num amount;
  final String currency;
  final String? terms;
  final String status;

  factory BookingQuoteData.fromJson(Map<String, dynamic> json) => BookingQuoteData(
    id: json['id'] as String,
    amount: json['amount'] as num,
    currency: json['currency'] as String,
    terms: json['terms'] as String?,
    status: json['status'] as String,
  );
}

class BookingStatusHistoryData {
  const BookingStatusHistoryData({
    required this.fromStatus,
    required this.toStatus,
    required this.reason,
    required this.createdAt,
  });

  final String? fromStatus;
  final String toStatus;
  final String? reason;
  final DateTime createdAt;

  factory BookingStatusHistoryData.fromJson(Map<String, dynamic> json) => BookingStatusHistoryData(
    fromStatus: json['from_status'] as String?,
    toStatus: json['to_status'] as String,
    reason: json['reason'] as String?,
    createdAt: DateTime.parse(json['created_at'] as String),
  );
}

class BookingSummaryData {
  const BookingSummaryData({
    required this.id,
    required this.artistProfileId,
    required this.artistDisplayName,
    required this.serviceName,
    required this.status,
    required this.requestedDate,
    required this.requestedTime,
  });

  final String id;
  final String artistProfileId;
  final String? artistDisplayName;
  final String? serviceName;
  final String status;
  final String? requestedDate;
  final String? requestedTime;

  factory BookingSummaryData.fromJson(Map<String, dynamic> json) => BookingSummaryData(
    id: json['id'] as String,
    artistProfileId: json['artist_profile_id'] as String,
    artistDisplayName: json['artist_display_name'] as String?,
    serviceName: json['service_name'] as String?,
    status: json['status'] as String,
    requestedDate: json['requested_date'] as String?,
    requestedTime: json['requested_time'] as String?,
  );
}

class BookingDetailData {
  const BookingDetailData({
    required this.id,
    required this.customerId,
    required this.artistProfileId,
    required this.artistDisplayName,
    required this.serviceId,
    required this.serviceName,
    required this.status,
    required this.requestedDate,
    required this.requestedTime,
    required this.locationType,
    required this.locationAddress,
    required this.eventType,
    required this.numCustomers,
    required this.notes,
    required this.contactName,
    required this.contactEmail,
    required this.contactPhone,
    required this.totalAmount,
    required this.depositAmount,
    required this.currency,
    required this.quotes,
    required this.statusHistory,
  });

  final String id;
  final String customerId;
  final String artistProfileId;
  final String? artistDisplayName;
  final String? serviceId;
  final String? serviceName;
  final String status;
  final String? requestedDate;
  final String? requestedTime;
  final String? locationType;
  final String? locationAddress;
  final String? eventType;
  final int? numCustomers;
  final String? notes;
  final String? contactName;
  final String? contactEmail;
  final String? contactPhone;
  final num? totalAmount;
  final num? depositAmount;
  final String currency;
  final List<BookingQuoteData> quotes;
  final List<BookingStatusHistoryData> statusHistory;

  factory BookingDetailData.fromJson(Map<String, dynamic> json) => BookingDetailData(
    id: json['id'] as String,
    customerId: json['customer_id'] as String,
    artistProfileId: json['artist_profile_id'] as String,
    artistDisplayName: json['artist_display_name'] as String?,
    serviceId: json['service_id'] as String?,
    serviceName: json['service_name'] as String?,
    status: json['status'] as String,
    requestedDate: json['requested_date'] as String?,
    requestedTime: json['requested_time'] as String?,
    locationType: json['location_type'] as String?,
    locationAddress: json['location_address'] as String?,
    eventType: json['event_type'] as String?,
    numCustomers: json['num_customers'] as int?,
    notes: json['notes'] as String?,
    contactName: json['contact_name'] as String?,
    contactEmail: json['contact_email'] as String?,
    contactPhone: json['contact_phone'] as String?,
    totalAmount: json['total_amount'] as num?,
    depositAmount: json['deposit_amount'] as num?,
    currency: json['currency'] as String,
    quotes: (json['quotes'] as List<dynamic>)
        .map((e) => BookingQuoteData.fromJson(e as Map<String, dynamic>))
        .toList(),
    statusHistory: (json['status_history'] as List<dynamic>)
        .map((e) => BookingStatusHistoryData.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}
