import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import '../../core/theme/design_tokens.dart';
import '../../core/widgets/widgets.dart';
import 'artist_models.dart';
import 'artist_repository.dart';

const _stepLabels = [
  'About you',
  'Location & services',
  'Contact & social',
  'Photos',
  'Documents',
  'Review',
];

/// Multi-step artist onboarding wizard — see docs/artist-verification.md.
/// Each step's "Continue" saves just that step's fields (`PATCH
/// /artist/profile`, server applies a partial update via `exclude_unset`),
/// mirroring the web wizard so progress is never lost if the app is closed
/// mid-flow.
///
/// Document uploads here are image-only (camera/gallery via [ImagePicker]):
/// the mobile app has no PDF picker dependency yet (`file_picker` isn't in
/// pubspec.yaml). A photo of an ID document is a common and acceptable
/// capture method, but PDF upload support should be added in a later phase
/// if needed.
class ArtistOnboardingScreen extends ConsumerStatefulWidget {
  const ArtistOnboardingScreen({super.key});

  @override
  ConsumerState<ArtistOnboardingScreen> createState() => _ArtistOnboardingScreenState();
}

class _ArtistOnboardingScreenState extends ConsumerState<ArtistOnboardingScreen> {
  bool _isLoading = true;
  String? _loadError;
  ArtistProfileData? _profile;
  List<ArtistDocumentData> _documents = [];

  int _step = 0;
  bool _isSaving = false;
  String? _stepError;

  // Uploading state, keyed by a stable tag so each button shows its own spinner.
  String? _uploadingTag;

  final _professionalNameController = TextEditingController();
  final _businessNameController = TextEditingController();
  final _headlineController = TextEditingController();
  final _bioController = TextEditingController();
  final _yearsExperienceController = TextEditingController();
  final _countryController = TextEditingController();
  final _cityController = TextEditingController();
  final _serviceAreasController = TextEditingController();
  final _languagesController = TextEditingController();
  final _contactEmailController = TextEditingController();
  final _contactPhoneController = TextEditingController();
  final Map<String, TextEditingController> _socialControllers = {
    for (final platform in const [
      'instagram',
      'facebook',
      'twitter',
      'tiktok',
      'youtube',
      'pinterest',
      'website',
    ])
      platform: TextEditingController(),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _professionalNameController.dispose();
    _businessNameController.dispose();
    _headlineController.dispose();
    _bioController.dispose();
    _yearsExperienceController.dispose();
    _countryController.dispose();
    _cityController.dispose();
    _serviceAreasController.dispose();
    _languagesController.dispose();
    _contactEmailController.dispose();
    _contactPhoneController.dispose();
    for (final controller in _socialControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final repository = ref.read(artistRepositoryProvider);
      final profile = await repository.fetchProfile();
      final documents = await repository.fetchDocuments();
      _professionalNameController.text = profile.professionalName ?? '';
      _businessNameController.text = profile.businessName ?? '';
      _headlineController.text = profile.headline ?? '';
      _bioController.text = profile.bio ?? '';
      _yearsExperienceController.text = profile.yearsExperience?.toString() ?? '';
      _countryController.text = profile.country ?? '';
      _cityController.text = profile.city ?? '';
      _serviceAreasController.text = profile.serviceAreas.join(', ');
      _languagesController.text = profile.languages.join(', ');
      _contactEmailController.text = profile.contactEmail ?? '';
      _contactPhoneController.text = profile.contactPhone ?? '';
      for (final entry in profile.socialLinks.entries) {
        _socialControllers[entry.key]?.text = entry.value;
      }
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _documents = documents;
        _isLoading = false;
      });
    } on ArtistException catch (e) {
      if (!mounted) return;
      setState(() {
        _loadError = e.message;
        _isLoading = false;
      });
    }
  }

  Future<void> _savePatchAndAdvance(Map<String, dynamic> patch) async {
    setState(() {
      _isSaving = true;
      _stepError = null;
    });
    try {
      final updated = await ref.read(artistRepositoryProvider).updateProfile(patch);
      if (!mounted) return;
      setState(() {
        _profile = updated;
        _step = (_step + 1).clamp(0, _stepLabels.length - 1);
      });
    } on ArtistException catch (e) {
      if (!mounted) return;
      setState(() => _stepError = e.message);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _refreshAfterUpload() async {
    final repository = ref.read(artistRepositoryProvider);
    final profile = await repository.fetchProfile();
    final documents = await repository.fetchDocuments();
    if (!mounted) return;
    setState(() {
      _profile = profile;
      _documents = documents;
    });
  }

  Future<void> _uploadProfileOrCoverImage({required bool isCover}) async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (picked == null) return;

    final tag = isCover ? 'cover_image' : 'profile_image';
    setState(() => _uploadingTag = tag);
    try {
      final bytes = await picked.readAsBytes();
      final repository = ref.read(artistRepositoryProvider);
      final imageUrl = isCover
          ? await repository.uploadCoverImage(
              bytes: bytes,
              filename: picked.name,
              contentType: picked.mimeType ?? 'image/jpeg',
            )
          : await repository.uploadProfileImage(
              bytes: bytes,
              filename: picked.name,
              contentType: picked.mimeType ?? 'image/jpeg',
            );
      if (!mounted) return;
      setState(() {
        _profile = isCover
            ? _profile!.copyWith(coverImageUrl: imageUrl)
            : _profile!.copyWith(profileImageUrl: imageUrl);
      });
    } on ArtistException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _uploadingTag = null);
    }
  }

  Future<void> _uploadIdentityDocument(String documentType) async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
    if (picked == null) return;

    setState(() => _uploadingTag = documentType);
    try {
      final bytes = await picked.readAsBytes();
      await ref
          .read(artistRepositoryProvider)
          .uploadDocument(
            bytes: bytes,
            filename: picked.name,
            contentType: picked.mimeType ?? 'image/jpeg',
            documentType: documentType,
          );
      await _refreshAfterUpload();
    } on ArtistException catch (e) {
      if (mounted) AppSnackBar.showError(context, e.message);
    } finally {
      if (mounted) setState(() => _uploadingTag = null);
    }
  }

  Future<void> _submit() async {
    setState(() {
      _isSaving = true;
      _stepError = null;
    });
    try {
      await ref.read(artistRepositoryProvider).submitProfile();
      if (!mounted) return;
      context.go('/artist/verification-status');
    } on ArtistException catch (e) {
      if (!mounted) return;
      setState(() => _stepError = e.message);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  List<String> _splitList(String value) {
    return value
        .split(',')
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Become a verified artist')),
      body: SafeArea(
        child: _isLoading
            ? const AppLoadingView(message: 'Loading your application…')
            : _loadError != null
            ? AppErrorState(message: _loadError!, onRetry: _load)
            : _buildWizard(context),
      ),
    );
  }

  Widget _buildWizard(BuildContext context) {
    final profile = _profile!;

    if (!profile.isEditable) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(Spacing.s6),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                "Your application can't be edited right now — it's currently "
                '${artistVerificationStatusLabels[profile.verificationStatus] ?? profile.verificationStatus}.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: Spacing.s4),
              AppPrimaryButton(
                label: 'View verification status',
                onPressed: () => context.go('/artist/verification-status'),
              ),
            ],
          ),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(Spacing.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: Spacing.s2,
            runSpacing: Spacing.s2,
            children: [
              for (var i = 0; i < _stepLabels.length; i++)
                Chip(
                  label: Text('${i + 1}. ${_stepLabels[i]}'),
                  backgroundColor: i == _step
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.surfaceContainerHighest,
                  labelStyle: TextStyle(
                    color: i == _step ? Theme.of(context).colorScheme.onPrimary : null,
                  ),
                ),
            ],
          ),
          const SizedBox(height: Spacing.s4),
          if (_stepError != null) ...[
            Text(_stepError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const SizedBox(height: Spacing.s3),
          ],
          _buildStep(profile),
        ],
      ),
    );
  }

  Widget _buildStep(ArtistProfileData profile) {
    switch (_step) {
      case 0:
        return _buildAboutYouStep();
      case 1:
        return _buildLocationStep();
      case 2:
        return _buildContactStep();
      case 3:
        return _buildPhotosStep(profile);
      case 4:
        return _buildDocumentsStep();
      default:
        return _buildReviewStep(profile);
    }
  }

  Widget _buildAboutYouStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextField(label: 'Professional name', controller: _professionalNameController),
        const SizedBox(height: Spacing.s3),
        AppTextField(label: 'Business name (optional)', controller: _businessNameController),
        const SizedBox(height: Spacing.s3),
        AppTextField(label: 'Headline (optional)', controller: _headlineController),
        const SizedBox(height: Spacing.s3),
        AppTextField(label: 'Biography', controller: _bioController),
        const SizedBox(height: Spacing.s3),
        AppTextField(
          label: 'Years of experience',
          controller: _yearsExperienceController,
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: Spacing.s6),
        AppPrimaryButton(
          label: 'Continue',
          isLoading: _isSaving,
          onPressed: () => _savePatchAndAdvance({
            'professional_name': _professionalNameController.text.trim().isEmpty
                ? null
                : _professionalNameController.text.trim(),
            'business_name': _businessNameController.text.trim().isEmpty
                ? null
                : _businessNameController.text.trim(),
            'headline': _headlineController.text.trim().isEmpty
                ? null
                : _headlineController.text.trim(),
            'bio': _bioController.text.trim().isEmpty ? null : _bioController.text.trim(),
            'years_experience': int.tryParse(_yearsExperienceController.text.trim()),
          }),
        ),
      ],
    );
  }

  Widget _buildLocationStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextField(label: 'Country (e.g. IN)', controller: _countryController),
        const SizedBox(height: Spacing.s3),
        AppTextField(label: 'City', controller: _cityController),
        const SizedBox(height: Spacing.s3),
        AppTextField(
          label: 'Service areas (comma-separated)',
          controller: _serviceAreasController,
        ),
        const SizedBox(height: Spacing.s3),
        AppTextField(label: 'Languages (comma-separated)', controller: _languagesController),
        const SizedBox(height: Spacing.s6),
        Row(
          children: [
            Expanded(
              child: AppSecondaryButton(
                label: 'Back',
                onPressed: () => setState(() => _step = 0),
              ),
            ),
            const SizedBox(width: Spacing.s3),
            Expanded(
              child: AppPrimaryButton(
                label: 'Continue',
                isLoading: _isSaving,
                onPressed: () => _savePatchAndAdvance({
                  'country': _countryController.text.trim().isEmpty
                      ? null
                      : _countryController.text.trim(),
                  'city': _cityController.text.trim().isEmpty
                      ? null
                      : _cityController.text.trim(),
                  'service_areas': _splitList(_serviceAreasController.text),
                  'languages': _splitList(_languagesController.text),
                }),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildContactStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextField(
          label: 'Contact email (optional)',
          controller: _contactEmailController,
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: Spacing.s3),
        AppTextField(label: 'Contact phone (optional)', controller: _contactPhoneController),
        for (final entry in _socialControllers.entries) ...[
          const SizedBox(height: Spacing.s3),
          AppTextField(
            label:
                '${entry.key[0].toUpperCase()}${entry.key.substring(1)} link (optional)',
            controller: entry.value,
          ),
        ],
        const SizedBox(height: Spacing.s6),
        Row(
          children: [
            Expanded(
              child: AppSecondaryButton(
                label: 'Back',
                onPressed: () => setState(() => _step = 1),
              ),
            ),
            const SizedBox(width: Spacing.s3),
            Expanded(
              child: AppPrimaryButton(
                label: 'Continue',
                isLoading: _isSaving,
                onPressed: () => _savePatchAndAdvance({
                  'contact_email': _contactEmailController.text.trim().isEmpty
                      ? null
                      : _contactEmailController.text.trim(),
                  'contact_phone': _contactPhoneController.text.trim().isEmpty
                      ? null
                      : _contactPhoneController.text.trim(),
                  'social_links': {
                    for (final entry in _socialControllers.entries)
                      if (entry.value.text.trim().isNotEmpty) entry.key: entry.value.text.trim(),
                  },
                }),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPhotosStep(ArtistProfileData profile) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Profile photo (optional)', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: Spacing.s2),
        if (profile.profileImageUrl != null)
          CircleAvatar(radius: IconSizes.xl, backgroundImage: NetworkImage(profile.profileImageUrl!)),
        const SizedBox(height: Spacing.s2),
        AppSecondaryButton(
          label: 'Choose photo',
          isLoading: _uploadingTag == 'profile_image',
          onPressed: () => _uploadProfileOrCoverImage(isCover: false),
        ),
        const SizedBox(height: Spacing.s6),
        Text('Cover photo (optional)', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: Spacing.s2),
        if (profile.coverImageUrl != null)
          AspectRatio(
            aspectRatio: 3,
            child: Image.network(profile.coverImageUrl!, fit: BoxFit.cover),
          ),
        const SizedBox(height: Spacing.s2),
        AppSecondaryButton(
          label: 'Choose cover photo',
          isLoading: _uploadingTag == 'cover_image',
          onPressed: () => _uploadProfileOrCoverImage(isCover: true),
        ),
        const SizedBox(height: Spacing.s6),
        Row(
          children: [
            Expanded(
              child: AppSecondaryButton(
                label: 'Back',
                onPressed: () => setState(() => _step = 2),
              ),
            ),
            const SizedBox(width: Spacing.s3),
            Expanded(
              child: AppPrimaryButton(
                label: 'Continue',
                onPressed: () => setState(() => _step = 4),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDocumentsStep() {
    final idDocument = _documents
        .where((doc) => doc.documentType == 'id_proof' && doc.status != 'rejected')
        .toList();
    final businessDocuments = _documents
        .where((doc) => doc.documentType == 'business_license')
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Identity document (required)', style: Theme.of(context).textTheme.titleSmall),
        Text(
          'A photo of a government-issued ID or passport.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        if (idDocument.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s2),
            child: Text('Uploaded — status: ${idDocument.first.status}'),
          ),
        const SizedBox(height: Spacing.s2),
        AppSecondaryButton(
          label: 'Upload identity document',
          isLoading: _uploadingTag == 'id_proof',
          onPressed: () => _uploadIdentityDocument('id_proof'),
        ),
        const SizedBox(height: Spacing.s6),
        Text('Business license (optional)', style: Theme.of(context).textTheme.titleSmall),
        for (final doc in businessDocuments)
          Padding(
            padding: const EdgeInsets.only(top: Spacing.s2),
            child: Text('Uploaded — status: ${doc.status}'),
          ),
        const SizedBox(height: Spacing.s2),
        AppSecondaryButton(
          label: 'Upload business license',
          isLoading: _uploadingTag == 'business_license',
          onPressed: () => _uploadIdentityDocument('business_license'),
        ),
        const SizedBox(height: Spacing.s6),
        Row(
          children: [
            Expanded(
              child: AppSecondaryButton(
                label: 'Back',
                onPressed: () => setState(() => _step = 3),
              ),
            ),
            const SizedBox(width: Spacing.s3),
            Expanded(
              child: AppPrimaryButton(
                label: 'Continue',
                onPressed: () => setState(() => _step = 5),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildReviewStep(ArtistProfileData profile) {
    final missing = profile.missingRequirements;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (missing.isNotEmpty)
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Before you can submit:', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: Spacing.s2),
                for (final requirement in missing)
                  Text('• ${artistMissingRequirementLabels[requirement] ?? requirement}'),
              ],
            ),
          )
        else
          Text(
            'Your application is complete. Submit it for review below.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        const SizedBox(height: Spacing.s6),
        Row(
          children: [
            Expanded(
              child: AppSecondaryButton(
                label: 'Back',
                onPressed: () => setState(() => _step = 4),
              ),
            ),
            const SizedBox(width: Spacing.s3),
            Expanded(
              child: AppPrimaryButton(
                label: 'Submit for review',
                isLoading: _isSaving,
                onPressed: missing.isEmpty ? _submit : null,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
