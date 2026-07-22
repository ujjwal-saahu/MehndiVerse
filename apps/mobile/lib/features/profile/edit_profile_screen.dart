import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'profile_repository.dart';

class EditProfileScreen extends ConsumerStatefulWidget {
  const EditProfileScreen({super.key});

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameController = TextEditingController();
  final _bioController = TextEditingController();
  final _cityController = TextEditingController();
  final _countryController = TextEditingController();

  bool _isLoading = true;
  bool _isSaving = false;
  bool _isUploadingAvatar = false;
  String? _errorMessage;
  String? _avatarUrl;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final profile = await ref.read(profileRepositoryProvider).fetchProfile();
      _displayNameController.text = profile.displayName;
      _bioController.text = profile.bio ?? '';
      _cityController.text = profile.city ?? '';
      _countryController.text = profile.country ?? '';
      setState(() {
        _avatarUrl = profile.avatarUrl;
        _isLoading = false;
      });
    } on ProfileException catch (e) {
      setState(() {
        _errorMessage = e.message;
        _isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _displayNameController.dispose();
    _bioController.dispose();
    _cityController.dispose();
    _countryController.dispose();
    super.dispose();
  }

  Future<void> _pickAndUploadAvatar() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (picked == null) return;

    setState(() => _isUploadingAvatar = true);
    try {
      final bytes = await picked.readAsBytes();
      final avatarUrl = await ref
          .read(profileRepositoryProvider)
          .uploadAvatar(
            bytes: bytes,
            filename: picked.name,
            contentType: picked.mimeType ?? 'image/jpeg',
          );
      if (mounted) {
        setState(() => _avatarUrl = avatarUrl);
        AppSnackBar.showSuccess(context, 'Avatar updated.');
      }
    } on ProfileException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isUploadingAvatar = false);
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      await ref
          .read(profileRepositoryProvider)
          .updateProfile(
            displayName: _displayNameController.text.trim(),
            bio: _bioController.text.trim().isEmpty ? null : _bioController.text.trim(),
            city: _cityController.text.trim().isEmpty ? null : _cityController.text.trim(),
            country: _countryController.text.trim().isEmpty
                ? null
                : _countryController.text.trim(),
          );
      if (mounted) {
        AppSnackBar.showSuccess(context, 'Profile updated.');
        Navigator.of(context).pop();
      }
    } on ProfileException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Edit profile')),
      body: _isLoading
          ? const AppLoadingView()
          : _errorMessage != null
          ? AppErrorState(message: _errorMessage!, onRetry: _load)
          : SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(Spacing.s6),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Stack(
                          children: [
                            CircleAvatar(
                              radius: IconSizes.xl,
                              backgroundImage: _avatarUrl != null
                                  ? NetworkImage(_avatarUrl!)
                                  : null,
                              child: _avatarUrl == null
                                  ? const Icon(Icons.person, size: IconSizes.lg)
                                  : null,
                            ),
                            Positioned(
                              bottom: 0,
                              right: 0,
                              child: IconButton.filled(
                                key: const Key('edit-profile-avatar-button'),
                                icon: _isUploadingAvatar
                                    ? const SizedBox(
                                        height: 16,
                                        width: 16,
                                        child: CircularProgressIndicator(strokeWidth: 2),
                                      )
                                    : const Icon(Icons.camera_alt, size: IconSizes.sm),
                                onPressed: _isUploadingAvatar ? null : _pickAndUploadAvatar,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: Spacing.s6),
                      AppTextField(
                        key: const Key('edit-profile-display-name-field'),
                        label: 'Display name',
                        controller: _displayNameController,
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return 'Display name is required.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: Spacing.s3),
                      AppTextField(
                        key: const Key('edit-profile-bio-field'),
                        label: 'Bio',
                        controller: _bioController,
                      ),
                      const SizedBox(height: Spacing.s3),
                      AppTextField(label: 'City', controller: _cityController),
                      const SizedBox(height: Spacing.s3),
                      AppTextField(label: 'Country (e.g. IN)', controller: _countryController),
                      const SizedBox(height: Spacing.s6),
                      AppPrimaryButton(
                        label: 'Save changes',
                        isLoading: _isSaving,
                        onPressed: _save,
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}
