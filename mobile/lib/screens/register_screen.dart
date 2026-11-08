import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../state/auth_provider.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _c = {for (final k in ['first_name', 'last_name', 'email', 'phone', 'password', 'confirm']) k: TextEditingController()};
  Map<String, String?> _errors = {};
  String? _error;
  bool _loading = false;

  @override
  void dispose() {
    for (final c in _c.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _loading = true; _errors = {}; _error = null; });
    try {
      await context.read<AuthProvider>().register({
        for (final k in ['first_name', 'last_name', 'email', 'phone', 'password']) k: _c[k]!.text.trim(),
      });
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } on ApiException catch (e) {
      setState(() {
        _errors = {for (final k in _c.keys) k: e.field(k)};
        if (_errors.values.every((v) => v == null)) _error = e.message;
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Widget _field(String key, String label, {bool obscure = false, TextInputType? type, String? Function(String?)? validator}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextFormField(
          controller: _c[key],
          obscureText: obscure,
          keyboardType: type,
          decoration: InputDecoration(labelText: label, errorText: _errors[key], errorMaxLines: 3),
          validator: validator ?? (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: SafeArea(
        child: Form(
          key: _form,
          child: ListView(padding: const EdgeInsets.all(20), children: [
            const Text('Free account: book anything from a parcel to a full container and follow every milestone.'),
            const SizedBox(height: 16),
            if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text(_error!, style: const TextStyle(color: Colors.red))),
            _field('first_name', 'First name'),
            _field('last_name', 'Last name'),
            _field('email', 'Email', type: TextInputType.emailAddress, validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null),
            _field('phone', 'Phone (e.g. +256 7XX XXX XXX)', type: TextInputType.phone),
            _field('password', 'Password (min 10 characters)', obscure: true,
                validator: (v) => (v == null || v.length < 10) ? 'At least 10 characters' : null),
            _field('confirm', 'Confirm password', obscure: true,
                validator: (v) => v != _c['password']!.text ? 'Passwords do not match' : null),
            const SizedBox(height: 8),
            FilledButton(onPressed: _loading ? null : _submit, child: Text(_loading ? 'Creating…' : 'Create account')),
          ]),
        ),
      ),
    );
  }
}
