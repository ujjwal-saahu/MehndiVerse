/// Mirrors app/schemas/preview.py — see docs/hand-foot-preview.md. Position
/// (`x`/`y`) is a fraction (0..1) of the photo's width/height, not pixels,
/// so the same transform renders correctly at any display size.
class OverlayTransform {
  const OverlayTransform({
    this.x = 0.5,
    this.y = 0.5,
    this.scale = 1.0,
    this.rotationDegrees = 0.0,
    this.flipHorizontal = false,
    this.opacity = 1.0,
  });

  final double x;
  final double y;
  final double scale;
  final double rotationDegrees;
  final bool flipHorizontal;
  final double opacity;

  OverlayTransform copyWith({
    double? x,
    double? y,
    double? scale,
    double? rotationDegrees,
    bool? flipHorizontal,
    double? opacity,
  }) {
    return OverlayTransform(
      x: x ?? this.x,
      y: y ?? this.y,
      scale: scale ?? this.scale,
      rotationDegrees: rotationDegrees ?? this.rotationDegrees,
      flipHorizontal: flipHorizontal ?? this.flipHorizontal,
      opacity: opacity ?? this.opacity,
    );
  }

  factory OverlayTransform.fromJson(Map<String, dynamic> json) {
    return OverlayTransform(
      x: (json['x'] as num?)?.toDouble() ?? 0.5,
      y: (json['y'] as num?)?.toDouble() ?? 0.5,
      scale: (json['scale'] as num?)?.toDouble() ?? 1.0,
      rotationDegrees: (json['rotation_degrees'] as num?)?.toDouble() ?? 0.0,
      flipHorizontal: json['flip_horizontal'] as bool? ?? false,
      opacity: (json['opacity'] as num?)?.toDouble() ?? 1.0,
    );
  }

  Map<String, dynamic> toJson() => {
    'x': x,
    'y': y,
    'scale': scale,
    'rotation_degrees': rotationDegrees,
    'flip_horizontal': flipHorizontal,
    'opacity': opacity,
  };
}

class PreviewDesignSummary {
  const PreviewDesignSummary({
    required this.id,
    required this.title,
    this.thumbnailUrl,
    required this.isPremium,
  });

  final String id;
  final String title;
  final String? thumbnailUrl;
  final bool isPremium;

  factory PreviewDesignSummary.fromJson(Map<String, dynamic> json) {
    return PreviewDesignSummary(
      id: json['id'] as String,
      title: json['title'] as String,
      thumbnailUrl: json['thumbnail_url'] as String?,
      isPremium: json['is_premium'] as bool,
    );
  }
}

class PreviewProjectData {
  const PreviewProjectData({
    required this.id,
    this.design,
    required this.sourceImageUrl,
    this.resultImageUrl,
    this.overlayTransform,
    this.sourceWidth,
    this.sourceHeight,
    required this.status,
    this.errorMessage,
    this.sharedWithBookingId,
  });

  final String id;
  final PreviewDesignSummary? design;
  final String sourceImageUrl;
  final String? resultImageUrl;
  final OverlayTransform? overlayTransform;
  final int? sourceWidth;
  final int? sourceHeight;
  final String status;
  final String? errorMessage;
  final String? sharedWithBookingId;

  factory PreviewProjectData.fromJson(Map<String, dynamic> json) {
    return PreviewProjectData(
      id: json['id'] as String,
      design: json['design'] == null
          ? null
          : PreviewDesignSummary.fromJson(json['design'] as Map<String, dynamic>),
      sourceImageUrl: json['source_image_url'] as String,
      resultImageUrl: json['result_image_url'] as String?,
      overlayTransform: json['overlay_transform'] == null
          ? null
          : OverlayTransform.fromJson(json['overlay_transform'] as Map<String, dynamic>),
      sourceWidth: json['source_width'] as int?,
      sourceHeight: json['source_height'] as int?,
      status: json['status'] as String,
      errorMessage: json['error_message'] as String?,
      sharedWithBookingId: json['shared_with_booking_id'] as String?,
    );
  }
}

class SharePreviewData {
  const SharePreviewData({required this.url, required this.expiresInSeconds});

  final String url;
  final int expiresInSeconds;

  factory SharePreviewData.fromJson(Map<String, dynamic> json) {
    return SharePreviewData(
      url: json['url'] as String,
      expiresInSeconds: json['expires_in_seconds'] as int,
    );
  }
}
