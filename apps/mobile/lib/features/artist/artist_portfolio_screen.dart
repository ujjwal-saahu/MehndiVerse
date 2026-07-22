import 'package:flutter/material.dart';

import '../../core/widgets/widgets.dart';

class ArtistPortfolioScreen extends StatelessWidget {
  const ArtistPortfolioScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const PlaceholderScreen(
      title: 'Portfolio',
      message: 'Upload and manage your portfolio designs here once artist profiles ship.',
      icon: Icons.photo_library_outlined,
    );
  }
}
