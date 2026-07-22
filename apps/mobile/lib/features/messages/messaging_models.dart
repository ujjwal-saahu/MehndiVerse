/// Mirrors the backend's booking-messaging schemas (see
/// app/schemas/messaging.py) — see docs/booking-messaging.md.
library;

class MessageData {
  const MessageData({
    required this.id,
    required this.senderId,
    required this.body,
    required this.attachmentUrl,
    required this.messageType,
    required this.isRead,
    required this.createdAt,
  });

  final String id;
  final String senderId;
  final String? body;
  final String? attachmentUrl;
  final String messageType;
  final bool isRead;
  final DateTime createdAt;

  factory MessageData.fromJson(Map<String, dynamic> json) => MessageData(
    id: json['id'] as String,
    senderId: json['sender_id'] as String,
    body: json['body'] as String?,
    attachmentUrl: json['attachment_url'] as String?,
    messageType: json['message_type'] as String,
    isRead: json['is_read'] as bool,
    createdAt: DateTime.parse(json['created_at'] as String),
  );
}

class MessagePageData {
  const MessagePageData({required this.items, required this.nextCursor, required this.hasMore});

  final List<MessageData> items;
  final String? nextCursor;
  final bool hasMore;

  factory MessagePageData.fromJson(Map<String, dynamic> json) => MessagePageData(
    items: (json['items'] as List<dynamic>)
        .map((e) => MessageData.fromJson(e as Map<String, dynamic>))
        .toList(),
    nextCursor: (json['page_info'] as Map<String, dynamic>)['next_cursor'] as String?,
    hasMore: (json['page_info'] as Map<String, dynamic>)['has_more'] as bool,
  );
}

class ConversationBookingContextData {
  const ConversationBookingContextData({
    required this.bookingId,
    required this.status,
    required this.serviceName,
  });

  final String bookingId;
  final String status;
  final String? serviceName;

  factory ConversationBookingContextData.fromJson(Map<String, dynamic> json) =>
      ConversationBookingContextData(
        bookingId: json['booking_id'] as String,
        status: json['status'] as String,
        serviceName: json['service_name'] as String?,
      );
}

class ConversationSummaryData {
  const ConversationSummaryData({
    required this.id,
    required this.booking,
    required this.otherPartyDisplayName,
    required this.lastMessagePreview,
    required this.unreadCount,
  });

  final String id;
  final ConversationBookingContextData booking;
  final String? otherPartyDisplayName;
  final String? lastMessagePreview;
  final int unreadCount;

  factory ConversationSummaryData.fromJson(Map<String, dynamic> json) => ConversationSummaryData(
    id: json['id'] as String,
    booking: ConversationBookingContextData.fromJson(json['booking'] as Map<String, dynamic>),
    otherPartyDisplayName: json['other_party_display_name'] as String?,
    lastMessagePreview: json['last_message_preview'] as String?,
    unreadCount: json['unread_count'] as int,
  );
}
