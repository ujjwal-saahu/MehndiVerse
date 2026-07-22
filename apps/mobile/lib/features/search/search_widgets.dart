import 'package:flutter/material.dart';

import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import '../gallery/gallery_models.dart';
import 'search_models.dart';

enum SearchPremiumFilter { any, free, premium }

/// One taxonomy axis (style/occasion/body_part/difficulty/density/region) —
/// see docs/design-search.md#category-filter-semantics: options within an
/// axis are OR'd, axes are AND'd together.
const _axisOrder = ['style', 'occasion', 'body_part', 'difficulty', 'density', 'region'];

const _axisLabels = {
  'style': 'Style',
  'occasion': 'Occasion',
  'body_part': 'Body Part',
  'difficulty': 'Difficulty',
  'density': 'Density',
  'region': 'Region',
};

const _sortOptions = [
  ('relevance', 'Relevance'),
  ('newest', 'Newest'),
  ('popular', 'Most Viewed'),
  ('most_saved', 'Most Saved'),
];

/// Filter panel shown as a modal bottom sheet — see
/// docs/design-search.md#filter-panel. Multi-select category checkboxes
/// (grouped by axis), a premium/free radio group, and a sort dropdown. Every
/// change is applied immediately (calls straight back to the search screen,
/// which re-runs the search), matching the web filter panel's behavior.
class SearchFilterSheet extends StatelessWidget {
  const SearchFilterSheet({
    required this.categories,
    required this.selectedCategoryIds,
    required this.onToggleCategory,
    required this.premium,
    required this.onPremiumChange,
    required this.sort,
    required this.onSortChange,
    required this.hasActiveFilters,
    required this.onClearAll,
    super.key,
  });

  final List<CategoryData> categories;
  final Set<String> selectedCategoryIds;
  final ValueChanged<String> onToggleCategory;
  final SearchPremiumFilter premium;
  final ValueChanged<SearchPremiumFilter> onPremiumChange;
  final String sort;
  final ValueChanged<String> onSortChange;
  final bool hasActiveFilters;
  final VoidCallback onClearAll;

  @override
  Widget build(BuildContext context) {
    final byAxis = [
      for (final axis in _axisOrder)
        (axis, categories.where((category) => category.categoryType == axis).toList()),
    ].where((entry) => entry.$2.isNotEmpty).toList();

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.s4),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Filters', style: Theme.of(context).textTheme.titleLarge),
                  if (hasActiveFilters)
                    AppTextActionButton(label: 'Clear filters', onPressed: onClearAll),
                ],
              ),
              const SizedBox(height: Spacing.s3),
              Text('Sort by', style: Theme.of(context).textTheme.labelLarge),
              const SizedBox(height: Spacing.s1),
              DropdownButton<String>(
                value: sort,
                isExpanded: true,
                items: [
                  for (final option in _sortOptions)
                    DropdownMenuItem(value: option.$1, child: Text(option.$2)),
                ],
                onChanged: (value) {
                  if (value != null) onSortChange(value);
                },
              ),
              const SizedBox(height: Spacing.s4),
              Text('Price', style: Theme.of(context).textTheme.labelLarge),
              RadioGroup<SearchPremiumFilter>(
                groupValue: premium,
                onChanged: (value) {
                  if (value != null) onPremiumChange(value);
                },
                child: const Row(
                  children: [
                    Expanded(
                      child: RadioListTile<SearchPremiumFilter>(
                        value: SearchPremiumFilter.any,
                        title: Text('Any'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                    Expanded(
                      child: RadioListTile<SearchPremiumFilter>(
                        value: SearchPremiumFilter.free,
                        title: Text('Free'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                    Expanded(
                      child: RadioListTile<SearchPremiumFilter>(
                        value: SearchPremiumFilter.premium,
                        title: Text('Premium'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                  ],
                ),
              ),
              for (final (axis, options) in byAxis) ...[
                const SizedBox(height: Spacing.s4),
                Text(_axisLabels[axis]!, style: Theme.of(context).textTheme.labelLarge),
                for (final category in options)
                  CheckboxListTile(
                    value: selectedCategoryIds.contains(category.id),
                    onChanged: (_) => onToggleCategory(category.id),
                    title: Text(category.name),
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Type-ahead suggestions shown under the search field while typing — see
/// docs/design-search.md#search-suggestions. Selecting a "design" suggestion
/// navigates straight to it; "category"/"artist" apply as filters instead.
class SearchSuggestionsList extends StatelessWidget {
  const SearchSuggestionsList({required this.suggestions, required this.onSelect, super.key});

  final List<SearchSuggestionData> suggestions;
  final ValueChanged<SearchSuggestionData> onSelect;

  @override
  Widget build(BuildContext context) {
    if (suggestions.isEmpty) return const SizedBox.shrink();

    return AppCard(
      padding: EdgeInsets.zero,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final suggestion in suggestions)
            ListTile(
              title: Text(suggestion.label),
              trailing: Text(
                switch (suggestion.type) {
                  'design' => 'Design',
                  'category' => 'Category',
                  'artist' => 'Artist',
                  _ => suggestion.type,
                },
                style: Theme.of(context).textTheme.bodySmall,
              ),
              onTap: () => onSelect(suggestion),
            ),
        ],
      ),
    );
  }
}

/// Per-user recent searches — see
/// docs/design-search.md#search-history-and-recent-searches. Renders nothing
/// once cleared/empty rather than showing an empty row.
class RecentSearchesRow extends StatelessWidget {
  const RecentSearchesRow({
    required this.items,
    required this.onSelect,
    required this.onClear,
    super.key,
  });

  final List<SearchHistoryItemData> items;
  final ValueChanged<String> onSelect;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Recent searches', style: Theme.of(context).textTheme.labelLarge),
              AppTextActionButton(label: 'Clear', onPressed: onClear),
            ],
          ),
          Wrap(
            spacing: Spacing.s2,
            runSpacing: Spacing.s2,
            children: [
              for (final item in items)
                ActionChip(label: Text(item.query), onPressed: () => onSelect(item.query)),
            ],
          ),
        ],
      ),
    );
  }
}
