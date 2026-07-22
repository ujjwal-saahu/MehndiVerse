/// Mirrors the backend's `ArtistProfileOut`/`ArtistDocumentOut` (see
/// app/schemas/artist.py) and the web app's src/lib/artist-types.ts — kept in
/// sync by hand across all three, same as every other feature's models.
class ArtistProfileData {
  const ArtistProfileData({
    required this.id,
    required this.userId,
    this.professionalName,
    this.businessName,
    this.headline,
    this.bio,
    this.yearsExperience,
    this.country,
    this.city,
    required this.serviceAreas,
    required this.languages,
    this.contactEmail,
    this.contactPhone,
    required this.socialLinks,
    this.profileImageUrl,
    this.coverImageUrl,
    required this.verificationStatus,
    this.submittedAt,
    this.reviewedAt,
    this.rejectionReason,
    this.moreInfoRequest,
    required this.isEditable,
    required this.missingRequirements,
  });

  final String id;
  final String userId;
  final String? professionalName;
  final String? businessName;
  final String? headline;
  final String? bio;
  final int? yearsExperience;
  final String? country;
  final String? city;
  final List<String> serviceAreas;
  final List<String> languages;
  final String? contactEmail;
  final String? contactPhone;
  final Map<String, String> socialLinks;
  final String? profileImageUrl;
  final String? coverImageUrl;
  final String verificationStatus;
  final DateTime? submittedAt;
  final DateTime? reviewedAt;
  final String? rejectionReason;
  final String? moreInfoRequest;
  final bool isEditable;
  final List<String> missingRequirements;

  ArtistProfileData copyWith({String? profileImageUrl, String? coverImageUrl}) {
    return ArtistProfileData(
      id: id,
      userId: userId,
      professionalName: professionalName,
      businessName: businessName,
      headline: headline,
      bio: bio,
      yearsExperience: yearsExperience,
      country: country,
      city: city,
      serviceAreas: serviceAreas,
      languages: languages,
      contactEmail: contactEmail,
      contactPhone: contactPhone,
      socialLinks: socialLinks,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      coverImageUrl: coverImageUrl ?? this.coverImageUrl,
      verificationStatus: verificationStatus,
      submittedAt: submittedAt,
      reviewedAt: reviewedAt,
      rejectionReason: rejectionReason,
      moreInfoRequest: moreInfoRequest,
      isEditable: isEditable,
      missingRequirements: missingRequirements,
    );
  }

  factory ArtistProfileData.fromJson(Map<String, dynamic> json) {
    return ArtistProfileData(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      professionalName: json['professional_name'] as String?,
      businessName: json['business_name'] as String?,
      headline: json['headline'] as String?,
      bio: json['bio'] as String?,
      yearsExperience: json['years_experience'] as int?,
      country: json['country'] as String?,
      city: json['city'] as String?,
      serviceAreas: (json['service_areas'] as List<dynamic>).cast<String>(),
      languages: (json['languages'] as List<dynamic>).cast<String>(),
      contactEmail: json['contact_email'] as String?,
      contactPhone: json['contact_phone'] as String?,
      socialLinks: (json['social_links'] as Map<String, dynamic>).cast<String, String>(),
      profileImageUrl: json['profile_image_url'] as String?,
      coverImageUrl: json['cover_image_url'] as String?,
      verificationStatus: json['verification_status'] as String,
      submittedAt: json['submitted_at'] == null
          ? null
          : DateTime.parse(json['submitted_at'] as String),
      reviewedAt: json['reviewed_at'] == null
          ? null
          : DateTime.parse(json['reviewed_at'] as String),
      rejectionReason: json['rejection_reason'] as String?,
      moreInfoRequest: json['more_info_request'] as String?,
      isEditable: json['is_editable'] as bool,
      missingRequirements: (json['missing_requirements'] as List<dynamic>).cast<String>(),
    );
  }
}

class ArtistDocumentData {
  const ArtistDocumentData({
    required this.id,
    required this.documentType,
    this.originalFilename,
    required this.contentType,
    required this.fileSizeBytes,
    required this.status,
    this.rejectionReason,
    this.reviewedAt,
    required this.viewUrl,
  });

  final String id;
  final String documentType;
  final String? originalFilename;
  final String contentType;
  final int fileSizeBytes;
  final String status;
  final String? rejectionReason;
  final DateTime? reviewedAt;
  // Short-lived signed URL — minted fresh on every fetch, never cached
  // beyond the current screen's lifetime. See
  // docs/artist-verification.md#short-lived-signed-urls.
  final String viewUrl;

  factory ArtistDocumentData.fromJson(Map<String, dynamic> json) {
    return ArtistDocumentData(
      id: json['id'] as String,
      documentType: json['document_type'] as String,
      originalFilename: json['original_filename'] as String?,
      contentType: json['content_type'] as String,
      fileSizeBytes: json['file_size_bytes'] as int,
      status: json['status'] as String,
      rejectionReason: json['rejection_reason'] as String?,
      reviewedAt: json['reviewed_at'] == null
          ? null
          : DateTime.parse(json['reviewed_at'] as String),
      viewUrl: json['view_url'] as String,
    );
  }
}

const artistMissingRequirementLabels = <String, String>{
  'professional_name': 'Professional name',
  'bio': 'Biography',
  'years_experience': 'Years of experience',
  'country': 'Country',
  'city': 'City',
  'identity_document': 'Identity document',
};

const artistVerificationStatusLabels = <String, String>{
  'draft': 'Draft',
  'submitted': 'Submitted — awaiting review',
  'under_review': 'Under review',
  'more_information_required': 'More information needed',
  'approved': 'Approved',
  'rejected': 'Rejected',
  'suspended': 'Suspended',
};
