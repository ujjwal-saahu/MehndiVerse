import 'package:flutter/material.dart';

/// Standard text input. Wraps [TextFormField] with the label/error styling
/// already applied via `InputDecorationTheme` (see AppTheme) — this widget
/// exists so screens don't repeat `InputDecoration(...)` boilerplate.
class AppTextField extends StatelessWidget {
  const AppTextField({
    required this.label,
    this.controller,
    this.obscureText = false,
    this.keyboardType,
    this.errorText,
    this.validator,
    this.autofillHints,
    this.textInputAction,
    super.key,
  });

  final String label;
  final TextEditingController? controller;
  final bool obscureText;
  final TextInputType? keyboardType;
  final String? errorText;
  final String? Function(String?)? validator;
  final Iterable<String>? autofillHints;
  final TextInputAction? textInputAction;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      validator: validator,
      autofillHints: autofillHints,
      textInputAction: textInputAction,
      decoration: InputDecoration(labelText: label, errorText: errorText),
    );
  }
}
