import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../gallery/gallery_models.dart';
import '../gallery/gallery_repository.dart';
import '../gallery/gallery_widgets.dart';
import 'search_models.dart';
import 'search_widgets.dart';

const _minSuggestionLength = 2;
const _suggestionDebounce = Duration(milliseconds: 300);

class _ArtistFilter {
  const _ArtistFilter({required this.id, required this.label});
  final String id;
  final String label;
}

/// Design search — see docs/design-search.md. Mirrors
/// features/home/home_screen.dart's structure (repository injected via
/// Riverpod, fetch state kept in plain `setState` fields). Filter/sort
/// changes re-run the search immediately; the keyword field only re-runs on
/// submit, separately from the debounced suggestions fetch.
class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _queryController = TextEditingController();
  Timer? _debounce;

  List<CategoryData> _categories = [];
  List<SearchSuggestionData> _suggestions = [];
  List<SearchHistoryItemData> _recentSearches = [];

  final Set<String> _categoryIds = {};
  SearchPremiumFilter _premium = SearchPremiumFilter.any;
  String _sort = 'relevance';
  _ArtistFilter? _artistFilter;

  List<DesignSummaryData> _items = [];
  PageInfoData? _pageInfo;
  bool _isLoading = true;
  bool _isLoadingMore = false;
  GalleryException? _error;

  bool get _hasActiveFilters =>
      _categoryIds.isNotEmpty ||
      _premium != SearchPremiumFilter.any ||
      _sort != 'relevance' ||
      _artistFilter != null;

  @override
  void initState() {
    super.initState();
    _loadCategories();
    _loadRecentSearches();
    _search();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _queryController.dispose();
    super.dispose();
  }

  void _loadCategories() {
    ref
        .read(galleryRepositoryProvider)
        .fetchCategories()
        .then((categories) {
          if (mounted) setState(() => _categories = categories);
        })
        .catchError((Object _) {
          // Filter panel categories are a progressive enhancement — fail silently.
        });
  }

  void _loadRecentSearches() {
    ref
        .read(searchRepositoryProvider)
        .fetchHistory()
        .then((history) {
          if (mounted) setState(() => _recentSearches = history);
        })
        .catchError((Object _) {
          // Recent searches are a progressive enhancement — fail silently.
        });
  }

  Future<void> _search({String? cursor}) async {
    setState(() {
      if (cursor == null) {
        _isLoading = true;
        _error = null;
      } else {
        _isLoadingMore = true;
      }
    });

    try {
      final result = await ref
          .read(searchRepositoryProvider)
          .search(
            query: _queryController.text.trim().isEmpty ? null : _queryController.text.trim(),
            categoryIds: _categoryIds.toList(),
            artistId: _artistFilter?.id,
            isPremium: switch (_premium) {
              SearchPremiumFilter.any => null,
              SearchPremiumFilter.free => false,
              SearchPremiumFilter.premium => true,
            },
            sort: _sort,
            cursor: cursor,
          );
      if (!mounted) return;
      setState(() {
        _items = cursor == null ? result.items : [..._items, ...result.items];
        _pageInfo = result.pageInfo;
        _isLoading = false;
        _isLoadingMore = false;
      });
      if (cursor == null) _loadRecentSearches();
    } on GalleryException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _isLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  void _onQueryChanged(String value) {
    setState(() {}); // refreshes the clear-icon's visibility
    _debounce?.cancel();
    final trimmed = value.trim();
    if (trimmed.length < _minSuggestionLength) {
      setState(() => _suggestions = []);
      return;
    }
    _debounce = Timer(_suggestionDebounce, () async {
      try {
        final results = await ref.read(searchRepositoryProvider).suggest(trimmed);
        if (mounted) setState(() => _suggestions = results);
      } catch (_) {
        if (mounted) setState(() => _suggestions = []);
      }
    });
  }

  void _onSubmitted(String value) {
    setState(() => _suggestions = []);
    _search();
  }

  void _onSelectSuggestion(SearchSuggestionData suggestion) {
    setState(() => _suggestions = []);
    if (suggestion.type == 'design') {
      context.push('/design/${suggestion.id}');
      return;
    }
    if (suggestion.type == 'artist') {
      setState(() {
        _queryController.clear();
        _artistFilter = _ArtistFilter(id: suggestion.id, label: suggestion.label);
      });
      _search();
      return;
    }
    if (!_categoryIds.contains(suggestion.id)) {
      setState(() {
        _queryController.clear();
        _categoryIds.add(suggestion.id);
      });
      _search();
    }
  }

  void _onSelectRecentSearch(String query) {
    setState(() {
      _queryController.text = query;
      _suggestions = [];
    });
    _search();
  }

  void _onClearHistory() {
    ref
        .read(searchRepositoryProvider)
        .clearHistory()
        .then((_) {
          if (mounted) setState(() => _recentSearches = []);
        })
        .catchError((Object _) {
          // Best-effort — the list simply won't clear if this fails.
        });
  }

  void _onClearArtistFilter() {
    setState(() => _artistFilter = null);
    _search();
  }

  void _onClearAllFilters() {
    setState(() {
      _categoryIds.clear();
      _premium = SearchPremiumFilter.any;
      _sort = 'relevance';
      _artistFilter = null;
    });
    _search();
  }

  void _openFilterSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return SearchFilterSheet(
              categories: _categories,
              selectedCategoryIds: _categoryIds,
              onToggleCategory: (id) {
                setModalState(() {
                  if (_categoryIds.contains(id)) {
                    _categoryIds.remove(id);
                  } else {
                    _categoryIds.add(id);
                  }
                });
                _search();
              },
              premium: _premium,
              onPremiumChange: (value) {
                setModalState(() => _premium = value);
                _search();
              },
              sort: _sort,
              onSortChange: (value) {
                setModalState(() => _sort = value);
                _search();
              },
              hasActiveFilters: _hasActiveFilters,
              onClearAll: () {
                setModalState(() {
                  _categoryIds.clear();
                  _premium = SearchPremiumFilter.any;
                  _sort = 'relevance';
                  _artistFilter = null;
                });
                _search();
              },
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Search')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(Spacing.s4, Spacing.s3, Spacing.s4, 0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _queryController,
                    onChanged: _onQueryChanged,
                    onSubmitted: _onSubmitted,
                    textInputAction: TextInputAction.search,
                    decoration: InputDecoration(
                      hintText: 'Search designs, styles, or artists…',
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _queryController.text.isEmpty
                          ? null
                          : IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                setState(() {
                                  _queryController.clear();
                                  _suggestions = [];
                                });
                              },
                            ),
                    ),
                  ),
                ),
                const SizedBox(width: Spacing.s2),
                IconButton(
                  icon: Icon(_hasActiveFilters ? Icons.tune : Icons.tune_outlined),
                  tooltip: 'Filters',
                  onPressed: _openFilterSheet,
                ),
              ],
            ),
          ),
          if (_suggestions.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.s4, vertical: Spacing.s2),
              child: SearchSuggestionsList(
                suggestions: _suggestions,
                onSelect: _onSelectSuggestion,
              ),
            ),
          RecentSearchesRow(
            items: _recentSearches,
            onSelect: _onSelectRecentSearch,
            onClear: _onClearHistory,
          ),
          if (_artistFilter != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.s4, vertical: Spacing.s2),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Chip(
                  label: Text('Artist: ${_artistFilter!.label}'),
                  onDeleted: _onClearArtistFilter,
                ),
              ),
            ),
          const SizedBox(height: Spacing.s2),
          Expanded(
            child: RefreshIndicator(onRefresh: () => _search(), child: _buildResults()),
          ),
        ],
      ),
    );
  }

  Widget _buildResults() {
    if (_isLoading) {
      return ListView(
        children: const [
          Padding(
            padding: EdgeInsets.only(top: Spacing.s16),
            child: AppLoadingView(message: 'Searching…'),
          ),
        ],
      );
    }
    if (_error != null) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s10),
            child: AppErrorState(message: _error!.message, onRetry: () => _search()),
          ),
        ],
      );
    }
    if (_items.isEmpty) {
      return ListView(
        children: [
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s10),
            child: AppEmptyState(
              title: 'No designs found',
              message: 'Try a different keyword or clear some filters.',
              icon: Icons.search_off_outlined,
              actionLabel: _hasActiveFilters ? 'Clear filters' : null,
              onAction: _hasActiveFilters ? _onClearAllFilters : null,
            ),
          ),
        ],
      );
    }

    return ListView(
      padding: const EdgeInsets.all(Spacing.s4),
      children: [
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            mainAxisSpacing: Spacing.s3,
            crossAxisSpacing: Spacing.s3,
            childAspectRatio: 0.72,
          ),
          itemCount: _items.length,
          itemBuilder: (context, index) => DesignThumbnailCard(design: _items[index]),
        ),
        if (_pageInfo?.hasMore == true)
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s4),
            child: Center(
              child: _isLoadingMore
                  ? const AppLoadingIndicator()
                  : AppSecondaryButton(
                      label: 'Load more',
                      onPressed: () => _search(cursor: _pageInfo!.nextCursor),
                    ),
            ),
          ),
      ],
    );
  }
}
