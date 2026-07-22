import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth/auth_models.dart';
import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    ref.read(authControllerProvider.notifier).login(
          email: _emailController.text.trim(),
          password: _passwordController.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final isLoading = authState is AuthStateAuthenticating;

    return Scaffold(
      appBar: AppBar(title: const Text('Log in')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Spacing.s6),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (authState is AuthStateError)
                  Padding(
                    padding: const EdgeInsets.only(bottom: Spacing.s4),
                    child: Text(
                      authState.message,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ),
                AppTextField(
                  key: const Key('login-email-field'),
                  label: 'Email',
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  textInputAction: TextInputAction.next,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) return 'Email is required.';
                    if (!value.contains('@')) return 'Enter a valid email address.';
                    return null;
                  },
                ),
                const SizedBox(height: Spacing.s3),
                AppTextField(
                  key: const Key('login-password-field'),
                  label: 'Password',
                  controller: _passwordController,
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  textInputAction: TextInputAction.done,
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'Password is required.';
                    return null;
                  },
                ),
                const SizedBox(height: Spacing.s6),
                AppPrimaryButton(label: 'Log in', isLoading: isLoading, onPressed: _submit),
                AppTextActionButton(
                  label: 'Forgot password?',
                  onPressed: () => context.push('/forgot-password'),
                ),
                AppTextActionButton(
                  label: "Don't have an account? Register",
                  onPressed: () => context.push('/register'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
