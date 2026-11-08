import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/auth_provider.dart';
import '../theme.dart';
import '../widgets/form_dialog.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final u = auth.user;
    if (u == null) return const SizedBox.shrink();
    return Scaffold(
      appBar: AppBar(title: const Text('My account')),
      body: RefreshIndicator(
        onRefresh: auth.loadMe,
        child: ListView(padding: const EdgeInsets.all(12), children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${u.firstName} ${u.lastName}', style: Theme.of(context).textTheme.titleLarge),
                Text(u.email),
                Text(u.phone),
                const Divider(height: 24),
                const Text('Your customer code'),
                Text(u.customerCode, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: amberDark, fontFamily: 'monospace')),
                Text(u.isDriver ? 'Driver account: trips allocated to you appear under Trips.' : 'Quote this code when you call us or drop cargo at a depot.'),
              ]),
            ),
          ),
          Card(
            child: Column(children: [
              ListTile(leading: const Icon(Icons.edit), title: const Text('Edit details'), onTap: () => _editProfile(context)),
              ListTile(leading: const Icon(Icons.lock_outline), title: const Text('Change password'), onTap: () => _changePassword(context)),
              ListTile(
                leading: const Icon(Icons.logout, color: Colors.red),
                title: const Text('Sign out', style: TextStyle(color: Colors.red)),
                onTap: () => context.read<AuthProvider>().logout(),
              ),
            ]),
          ),
        ]),
      ),
    );
  }

  Future<void> _editProfile(BuildContext context) async {
    final auth = context.read<AuthProvider>();
    final u = auth.user!;
    // Controllers are left to GC: disposing them here would race the dialog's
    // closing animation, which still renders the fields.
    final fn = TextEditingController(text: u.firstName);
    final ln = TextEditingController(text: u.lastName);
    final ph = TextEditingController(text: u.phone);
    final saved = await showFormDialog(
      context,
      title: 'Edit details',
      subtitle: 'Your email (${u.email}) cannot be changed here.',
      icon: Icons.person_outline,
      submitLabel: 'Save',
      onSubmit: () => auth.updateProfile({'first_name': fn.text.trim(), 'last_name': ln.text.trim(), 'phone': ph.text.trim()}),
      children: [
        Row(children: [
          Expanded(child: TextField(controller: fn, textCapitalization: TextCapitalization.words, maxLength: 150, decoration: const InputDecoration(labelText: 'First name', counterText: ''))),
          const SizedBox(width: 12),
          Expanded(child: TextField(controller: ln, textCapitalization: TextCapitalization.words, maxLength: 150, decoration: const InputDecoration(labelText: 'Last name', counterText: ''))),
        ]),
        TextField(
          controller: ph,
          keyboardType: TextInputType.phone,
          maxLength: 20,
          decoration: const InputDecoration(labelText: 'Phone', hintText: '+256 7XX XXX XXX', prefixIcon: Icon(Icons.phone_outlined), counterText: ''),
        ),
      ],
    );
    if (saved && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Details saved')));
    }
  }

  Future<void> _changePassword(BuildContext context) async {
    final auth = context.read<AuthProvider>();
    final cur = TextEditingController();
    final next = TextEditingController();
    final confirm = TextEditingController();
    await showFormDialog(
      context,
      title: 'Change password',
      subtitle: 'Use at least 10 characters.',
      icon: Icons.lock_reset,
      submitLabel: 'Change',
      onSubmit: () async {
        // Checked here so a typo never reaches the server or signs anyone out.
        if (next.text.isEmpty) throw const FormError('Enter a new password.');
        if (next.text != confirm.text) throw const FormError('The new passwords do not match.');
        await auth.changePassword(cur.text, next.text);
      },
      footnote: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(Icons.info_outline, size: 16, color: Color(0xFF5B6878)),
        SizedBox(width: 8),
        Expanded(child: Text('You will be signed out on all devices and need to sign in again.', style: TextStyle(fontSize: 12.5, color: Color(0xFF5B6878)))),
      ]),
      children: [
        PasswordField(controller: cur, label: 'Current password', autofillHints: const [AutofillHints.password]),
        PasswordField(controller: next, label: 'New password', autofillHints: const [AutofillHints.newPassword]),
        PasswordField(controller: confirm, label: 'Confirm new password', autofillHints: const [AutofillHints.newPassword]),
      ],
    );
  }
}
