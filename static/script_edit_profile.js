/**
 * Preview selected profile pic.
 */
function previewImage() {
  const input = document.getElementById('fileInput'),
        img   = document.getElementById('currentPicture');
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = e => img.src = e.target.result;
    reader.readAsDataURL(input.files[0]);
  }
}

/**
 * Toggle password visibility.
 */
function togglePassword(id) {
  const input = document.getElementById(id),
        icon = input.nextElementSibling.querySelector('i');
  if (input.type === 'password') {
    input.type = 'text';
    icon.classList.replace('fa-eye', 'fa-eye-slash');
  } else {
    input.type = 'password';
    icon.classList.replace('fa-eye-slash', 'fa-eye');
  }
}

/**
 * Open/close modal for changing password.
 */
function openPasswordModal() {
  const modal = document.getElementById('passwordModal');
  modal.style.display = 'block';
  document.body.style.overflow = 'hidden';
}

function closePasswordModal() {
  const modal = document.getElementById('passwordModal');
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
  document.getElementById('passwordForm').reset();
}

window.onclick = e => {
  if (e.target === document.getElementById('passwordModal')) {
    closePasswordModal();
  }
};

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closePasswordModal();
});

/**
 * Show notifications at top. Type: 'success'|'error'
 */
function showNotification(msg, type) {
  const n = document.getElementById('notification');
  n.textContent = msg;
  n.className = 'notification ' + type;
  n.classList.add('show');
  setTimeout(() => n.classList.remove('show'), 3000);
}

/**
 * Handle password form submission.
 */
document.getElementById('passwordForm').addEventListener('submit', async function(e){
  e.preventDefault();
  const current = document.getElementById('currentPassword').value,
        next    = document.getElementById('newPassword').value,
        confirm = document.getElementById('confirmPassword').value,
        btn     = document.getElementById('changePasswordBtn'),
        loading = document.getElementById('passwordLoading');

  if (next.length < 6) {
    showNotification('New password must be ≥ 6 characters.', 'error');
    return;
  }
  if (next !== confirm) {
    showNotification('New passwords do not match.', 'error');
    return;
  }

  btn.disabled = true;
  loading.style.display = 'inline';

  try {
    const res = await fetch('/api/change_password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_password: current,
        new_password: next,
        confirm_password: confirm
      })
    });
    const data = await res.json();
    showNotification(data.message, data.success ? 'success' : 'error');
    if (data.success) closePasswordModal();
  } catch(err) {
    console.error(err);
    showNotification('Error changing password. Try again.', 'error');
  } finally {
    btn.disabled = false;
    loading.style.display = 'none';
  }
});
