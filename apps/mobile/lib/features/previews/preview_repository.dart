import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

import 'preview_models.dart';

class PreviewException implements Exception {
  PreviewException(this.message);
  final String message;
}

/// Hand/foot design preview projects — see docs/hand-foot-preview.md. The
/// photo only ever reaches this repository (and the backend) once the user
/// explicitly saves/exports/shares/sends a project — all move/resize/
/// rotate/flip/opacity editing happens locally in
/// `preview_studio_screen.dart` first. Talks only to MehndiVerse's own
/// backend (`/api/v1/previews/*`), same boundary as every other repository.
class PreviewRepository {
  PreviewRepository(this._dio);

  final Dio _dio;

  Future<List<PreviewProjectData>> fetchMine() async {
    try {
      final response = await _dio.get<List<dynamic>>('/api/v1/previews/mine');
      return response.data!
          .map((entry) => PreviewProjectData.fromJson(entry as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<PreviewProjectData> fetchOne(String previewId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/previews/$previewId');
      return PreviewProjectData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<PreviewProjectData> create({
    required List<int> photoBytes,
    required String filename,
    String? designId,
    required OverlayTransform transform,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          photoBytes,
          filename: filename,
          contentType: MediaType.parse('image/jpeg'),
        ),
        'design_id': ?designId,
        'overlay_transform': _encodeTransform(transform),
      });
      final response = await _dio.post<Map<String, dynamic>>('/api/v1/previews', data: formData);
      return PreviewProjectData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<PreviewProjectData> update(
    String previewId, {
    List<int>? photoBytes,
    String? filename,
    String? designId,
    OverlayTransform? transform,
  }) async {
    try {
      final formData = FormData.fromMap({
        if (photoBytes != null)
          'file': MultipartFile.fromBytes(
            photoBytes,
            filename: filename ?? 'photo.jpg',
            contentType: MediaType.parse('image/jpeg'),
          ),
        'design_id': ?designId,
        if (transform != null) 'overlay_transform': _encodeTransform(transform),
      });
      final response = await _dio.patch<Map<String, dynamic>>(
        '/api/v1/previews/$previewId',
        data: formData,
      );
      return PreviewProjectData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<String> export(String previewId, {required List<int> compositeBytes}) async {
    try {
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          compositeBytes,
          filename: 'export.png',
          contentType: MediaType.parse('image/png'),
        ),
      });
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/previews/$previewId/export',
        data: formData,
      );
      return response.data!['result_image_url'] as String;
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<SharePreviewData> share(String previewId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/v1/previews/$previewId/share');
      return SharePreviewData.fromJson(response.data!);
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<void> sendToArtist(String previewId, {required String bookingId}) async {
    try {
      await _dio.post<void>(
        '/api/v1/previews/$previewId/send-to-artist',
        data: {'booking_id': bookingId},
      );
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  Future<void> delete(String previewId) async {
    try {
      await _dio.delete<void>('/api/v1/previews/$previewId');
    } on DioException catch (e) {
      throw _toException(e);
    }
  }

  String _encodeTransform(OverlayTransform transform) => jsonEncode(transform.toJson());

  PreviewException _toException(DioException e) {
    final data = e.response?.data;
    if (data is Map && data['error'] is Map && data['error']['message'] is String) {
      return PreviewException(data['error']['message'] as String);
    }
    return PreviewException(e.message ?? 'Something went wrong. Please try again.');
  }
}
