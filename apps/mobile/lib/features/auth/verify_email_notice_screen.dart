import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';

class VerifyEmailNoticeScreen extends ConsumerWidget {
  const VerifyEmailNoticeScreen({required this.email, super.key});

  final String email;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Check your email')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(Spacing.s6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('We sent a verification link to $email.'),
              const SizedBox(height: Spacing.s6),
              AppSecondaryButton(
                label: 'Resend verification email',
                onPressed: () => ref.read(authControllerProvider.notifier).resendVerification(email),
              ),
              const SizedBox(height: Spacing.s3),
              AppTextActionButton(label: 'Back to login', onPressed: () => context.go('/login')),
            ],
          ),
        ),
      ),
    );
  }
}
