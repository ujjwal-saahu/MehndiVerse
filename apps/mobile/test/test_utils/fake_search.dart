import 'package:mobile/features/gallery/gallery_models.dart';
import 'package:mobile/features/gallery/gallery_repository.dart';
import 'package:mobile/features/search/search_models.dart';
import 'package:mobile/features/search/search_repository.dart';

/// In-memory stand-in for [SearchRepository] so search widget tests never
/// touch a real backend (mirrors test_utils/fake_gallery.dart's approach).
class FakeSearchRepository implements SearchRepository {
  FakeSearchRepository({
    DesignListData? results,
    List<SearchSuggestionData>? suggestions,
    List<SearchHistoryItemData>? history,
    this.searchError,
  }) : results = results ?? const DesignListData(
         items: [],
         pageInfo: PageInfoData(nextCursor: null, hasMore: false),
       ),
       suggestions = suggestions ?? [],
       history = history ?? [];

  DesignListData results;
  List<SearchSuggestionData> suggestions;
  List<SearchHistoryItemData> history;
  GalleryException? searchError;
  final List<Map<String, dynamic>> recordedSearches = [];
  bool historyCleared = false;

  @override
  Future<DesignListData> search({
    String? query,
    List<String> categoryIds = const [],
    String? artistId,
    bool? isPremium,
    String sort = 'relevance',
    String? cursor,
    int limit = 20,
  }) async {
    recordedSearches.add({
      'query': query,
      'categoryIds': categoryIds,
      'artistId': artistId,
      'isPremium': isPremium,
      'sort': sort,
      'cursor': cursor,
    });
    if (searchError != null) throw searchError!;
    return results;
  }

  @override
  Future<List<SearchSuggestionData>> suggest(String query) async => suggestions;

  @override
  Future<List<SearchHistoryItemData>> fetchHistory() async => history;

  @override
  Future<void> clearHistory() async {
    historyCleared = true;
    history = [];
  }
}
