// my_music.js - Handle remove, export functionality on My Music page

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

// Export menu toggle
document.querySelectorAll('.export-btn').forEach(btn => {
  const menu = btn.nextElementSibling;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    // Close all other menus
    document.querySelectorAll('.export-menu').forEach(m => {
      if (m !== menu) m.style.display = 'none';
    });
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  });
});

document.addEventListener('click', () => {
  document.querySelectorAll('.export-menu').forEach(m => {
    m.style.display = 'none';
  });
});

// Export CSV
document.querySelectorAll('.export-csv-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const albumId = btn.getAttribute('data-album-id');
    // Fetch ranking data from result page or API
    try {
      const response = await fetch(`/rank/${albumId}/result/`);
      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const scriptTag = doc.querySelector('script');
      if (scriptTag) {
        // Extract data from script tag (simplified - in production, use API endpoint)
        alert('Please use the export feature from the ranking result page for full functionality.');
      }
    } catch (e) {
      alert('Error exporting CSV');
    }
  });
});

// Export PNG
document.querySelectorAll('.export-png-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const albumId = btn.getAttribute('data-album-id');
    // Redirect to result page for export
    window.location.href = `/rank/${albumId}/result/`;
  });
});

