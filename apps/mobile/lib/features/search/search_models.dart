/// Mirrors the backend's design-search schemas (see app/schemas/search.py).
/// Plain hand-written classes, not freezed — same call made for
/// gallery_models.dart.
library;

class SearchSuggestionData {
  const SearchSuggestionData({required this.type, required this.id, required this.label});

  final String type;
  final String id;
  final String label;

  factory SearchSuggestionData.fromJson(Map<String, dynamic> json) {
    return SearchSuggestionData(
      type: json['type'] as String,
      id: json['id'] as String,
      label: json['label'] as String,
    );
  }
}

class SearchHistoryItemData {
  const SearchHistoryItemData({required this.id, required this.query, required this.createdAt});

  final String id;
  final String query;
  final String createdAt;

  factory SearchHistoryItemData.fromJson(Map<String, dynamic> json) {
    return SearchHistoryItemData(
      id: json['id'] as String,
      query: json['query'] as String,
      createdAt: json['created_at'] as String,
    );
  }
}
