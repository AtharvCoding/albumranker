// my_music.js - Handle remove functionality on My Music page

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Remove button handlers
document.querySelectorAll('.remove-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to remove this album from your collection?')) {
      return;
    }
    
    const albumId = btn.getAttribute('data-album-id');
    const token = csrfToken || getCookie('csrftoken');
    try {
      const response = await fetch(`/api/unsave-album/${albumId}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        // Remove the card from DOM
        btn.closest('.album-card').remove();
      } else {
        alert('Error removing album');
      }
    } catch (e) {
      alert('Error removing album');
    }
  });
});

