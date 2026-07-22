/// Mirrors the backend's like/save schemas (see app/schemas/engagement.py).
library;

class LikeStatusData {
  const LikeStatusData({required this.liked, required this.likeCount});

  final bool liked;
  final int likeCount;

  factory LikeStatusData.fromJson(Map<String, dynamic> json) {
    return LikeStatusData(liked: json['liked'] as bool, likeCount: json['like_count'] as int);
  }
}

class SaveStatusData {
  const SaveStatusData({required this.saved, required this.saveCount});

  final bool saved;
  final int saveCount;

  factory SaveStatusData.fromJson(Map<String, dynamic> json) {
    return SaveStatusData(saved: json['saved'] as bool, saveCount: json['save_count'] as int);
  }
}
