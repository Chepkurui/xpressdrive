import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../theme.dart';

/// Thrown from an [showFormDialog] onSubmit to show [message] in the dialog.
class FormError implements Exception {
  const FormError(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Opens a wide form dialog with a header, the given fields and a full-width
/// action row. [onSubmit] runs inside the dialog: while it runs the buttons are
/// disabled; if it throws, the error is shown in the dialog (which stays open
/// so the user can correct it); on success the dialog closes and returns true.
Future<bool> showFormDialog(
  BuildContext context, {
  required String title,
  required IconData icon,
  String? subtitle,
  required List<Widget> children,
  required String submitLabel,
  required Future<void> Function() onSubmit,
  Widget? footnote,
}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => _FormDialog(
      title: title,
      icon: icon,
      subtitle: subtitle,
      submitLabel: submitLabel,
      onSubmit: onSubmit,
      footnote: footnote,
      children: children,
    ),
  );
  return ok == true;
}

class _FormDialog extends StatefulWidget {
  const _FormDialog({
    required this.title,
    required this.icon,
    required this.subtitle,
    required this.children,
    required this.submitLabel,
    required this.onSubmit,
    required this.footnote,
  });

  final String title, submitLabel;
  final String? subtitle;
  final IconData icon;
  final List<Widget> children;
  final Future<void> Function() onSubmit;
  final Widget? footnote;

  @override
  State<_FormDialog> createState() => _FormDialogState();
}

class _FormDialogState extends State<_FormDialog> {
  bool _busy = false;
  String? _error;

  Future<void> _submit() async {
    setState(() { _busy = true; _error = null; });
    try {
      await widget.onSubmit();
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() { _busy = false; _error = switch (e) { ApiException() => e.message, FormError() => e.message, _ => 'Something went wrong. Please try again.' }; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      clipBehavior: Clip.antiAlias,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            // Header
            Container(
              color: canvas,
              padding: const EdgeInsets.fromLTRB(20, 18, 8, 18),
              child: Row(children: [
                Container(
                  width: 42, height: 42,
                  decoration: BoxDecoration(color: navy, borderRadius: BorderRadius.circular(12)),
                  child: Icon(widget.icon, color: amber, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(widget.title, style: text.titleLarge?.copyWith(fontWeight: FontWeight.w700, color: navy)),
                    if (widget.subtitle != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(widget.subtitle!, style: text.bodySmall?.copyWith(color: const Color(0xFF5B6878))),
                      ),
                  ]),
                ),
                IconButton(tooltip: 'Close', onPressed: _busy ? null : () => Navigator.pop(context, false), icon: const Icon(Icons.close)),
              ]),
            ),
            const Divider(height: 1, color: Color(0xFFE0E6EE)),
            // Fields
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 4),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                for (var i = 0; i < widget.children.length; i++) ...[
                  if (i > 0) const SizedBox(height: 14),
                  widget.children[i],
                ],
                if (widget.footnote != null) ...[const SizedBox(height: 14), widget.footnote!],
                if (_error != null) ...[
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF3F2),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFFFECDCA)),
                    ),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const Icon(Icons.error_outline, size: 18, color: Color(0xFFB42318)),
                      const SizedBox(width: 8),
                      Expanded(child: Text(_error!, style: const TextStyle(color: Color(0xFFB42318), fontSize: 13))),
                    ]),
                  ),
                ],
              ]),
            ),
            // Actions
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
              child: Row(children: [
                Expanded(
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                    onPressed: _busy ? null : () => Navigator.pop(context, false),
                    child: const Text('Cancel'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: _busy ? null : _submit,
                    child: _busy
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
                        : Text(widget.submitLabel),
                  ),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

/// A password field with a show/hide toggle, for use inside form dialogs.
class PasswordField extends StatefulWidget {
  const PasswordField({super.key, required this.controller, required this.label, this.helper, this.autofillHints});
  final TextEditingController controller;
  final String label;
  final String? helper;
  final Iterable<String>? autofillHints;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _hidden = true;

  @override
  Widget build(BuildContext context) => TextField(
        controller: widget.controller,
        obscureText: _hidden,
        enableSuggestions: false,
        autocorrect: false,
        autofillHints: widget.autofillHints,
        decoration: InputDecoration(
          labelText: widget.label,
          helperText: widget.helper,
          prefixIcon: const Icon(Icons.lock_outline),
          suffixIcon: IconButton(
            tooltip: _hidden ? 'Show password' : 'Hide password',
            icon: Icon(_hidden ? Icons.visibility_outlined : Icons.visibility_off_outlined),
            onPressed: () => setState(() => _hidden = !_hidden),
          ),
        ),
      );
}
