/// Shapes returned by the backend's community-and-trust endpoints — see
/// app/schemas/comment.py, app/schemas/review.py, app/schemas/moderation.py
/// and docs/community-and-trust.md. Mirrors
/// apps/web/src/lib/community-types.ts.
class ReplyData {
  const ReplyData({
    required this.id,
    required this.designId,
    required this.userId,
    this.userDisplayName,
    required this.parentCommentId,
    required this.body,
    required this.createdAt,
  });

  final String id;
  final String designId;
  final String userId;
  final String? userDisplayName;
  final String parentCommentId;
  final String body;
  final DateTime createdAt;

  factory ReplyData.fromJson(Map<String, dynamic> json) {
    return ReplyData(
      id: json['id'] as String,
      designId: json['design_id'] as String,
      userId: json['user_id'] as String,
      userDisplayName: json['user_display_name'] as String?,
      parentCommentId: json['parent_comment_id'] as String,
      body: json['body'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class CommentData {
  const CommentData({
    required this.id,
    required this.designId,
    required this.userId,
    this.userDisplayName,
    required this.body,
    required this.replies,
    required this.createdAt,
  });

  final String id;
  final String designId;
  final String userId;
  final String? userDisplayName;
  final String body;
  final List<ReplyData> replies;
  final DateTime createdAt;

  factory CommentData.fromJson(Map<String, dynamic> json) {
    return CommentData(
      id: json['id'] as String,
      designId: json['design_id'] as String,
      userId: json['user_id'] as String,
      userDisplayName: json['user_display_name'] as String?,
      body: json['body'] as String,
      replies: (json['replies'] as List<dynamic>)
          .map((entry) => ReplyData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class ReviewData {
  const ReviewData({
    required this.id,
    required this.bookingId,
    required this.customerId,
    this.customerDisplayName,
    required this.artistProfileId,
    required this.rating,
    this.body,
    required this.createdAt,
  });

  final String id;
  final String bookingId;
  final String customerId;
  final String? customerDisplayName;
  final String artistProfileId;
  final int rating;
  final String? body;
  final DateTime createdAt;

  factory ReviewData.fromJson(Map<String, dynamic> json) {
    return ReviewData(
      id: json['id'] as String,
      bookingId: json['booking_id'] as String,
      customerId: json['customer_id'] as String,
      customerDisplayName: json['customer_display_name'] as String?,
      artistProfileId: json['artist_profile_id'] as String,
      rating: json['rating'] as int,
      body: json['body'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class ReviewListData {
  const ReviewListData({required this.items, required this.ratingAverage, required this.ratingCount});

  final List<ReviewData> items;
  final double ratingAverage;
  final int ratingCount;

  factory ReviewListData.fromJson(Map<String, dynamic> json) {
    return ReviewListData(
      items: (json['items'] as List<dynamic>)
          .map((entry) => ReviewData.fromJson(entry as Map<String, dynamic>))
          .toList(),
      ratingAverage: (json['rating_average'] as num).toDouble(),
      ratingCount: json['rating_count'] as int,
    );
  }
}
