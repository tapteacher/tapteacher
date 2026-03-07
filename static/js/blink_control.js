// Blink Control Script
document.addEventListener('DOMContentLoaded', function () {
    const SEEN_KEY = 'seen_institutes';

    function getSeenList() {
        const stored = localStorage.getItem(SEEN_KEY);
        return stored ? JSON.parse(stored) : [];
    }

    function addToSeen(id) {
        let seen = getSeenList();
        if (!seen.includes(id)) {
            seen.push(id);
            localStorage.setItem(SEEN_KEY, JSON.stringify(seen));
        }
    }

    function removeFromSeen(id) {
        let seen = getSeenList();
        const index = seen.indexOf(id);
        if (index > -1) {
            seen.splice(index, 1);
            localStorage.setItem(SEEN_KEY, JSON.stringify(seen));
        }
    }

    // Initialize Blinking Logic for Cards
    const candidates = document.querySelectorAll('.blink-candidate');
    const seenList = getSeenList();

    candidates.forEach(card => {
        const id = parseInt(card.dataset.instituteId);
        const toggle = card.querySelector('.blink-toggle');

        // GUEST Logic - Client Side Init
        if (!IS_AUTHENTICATED) {
            if (!seenList.includes(id)) {
                // Not seen yet - BLINKING
                card.classList.add('blink-red');
                if (toggle) toggle.checked = false; // Unchecked = blinking
            } else {
                // Seen - NOT BLINKING
                card.classList.remove('blink-red');
                if (toggle) toggle.checked = true; // Checked = marked as read
            }
        }
        // AUTH Logic - Server already rendered correct class/checked state. No JS init needed.

        // Handle Toggle Click
        if (toggle) {
            toggle.addEventListener('change', (e) => {
                e.stopPropagation();
                if (IS_AUTHENTICATED) {
                    // Server Sync
                    // Checked = mark as read, Unchecked = mark as unread
                    const action = e.target.checked ? 'mark_read' : 'mark_unread';
                    // Optimistic UI update
                    if (e.target.checked) card.classList.remove('blink-red'); // Checked = stop blinking
                    else card.classList.add('blink-red'); // Unchecked = start blinking

                    fetch(`/api/toggle-read/${id}/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ action: action })
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                // Reload page to update cascade (district/state/category blink status)
                                setTimeout(() => location.reload(), 300);
                            }
                        })
                        .catch(error => {
                            console.error('Toggle error:', error);
                            // Revert optimistic update on error
                            if (e.target.checked) card.classList.add('blink-red');
                            else card.classList.remove('blink-red');
                            e.target.checked = !e.target.checked;
                        });
                } else {
                    // Guest LocalStorage
                    // Checked = mark as read, Unchecked = mark as unread
                    if (e.target.checked) {
                        addToSeen(id); // Mark as read
                        card.classList.remove('blink-red'); // Stop blinking
                    } else {
                        removeFromSeen(id); // Mark as unread
                        card.classList.add('blink-red'); // Start blinking
                    }
                }
            });
        }
    });

    // Make handleCardClick global so onclick attribute can find it
    window.handleCardClick = function (element) {
        const id = parseInt(element.dataset.instituteId);
        const url = element.dataset.url;

        if (IS_AUTHENTICATED) {
            // Mark read on server, then navigate
            fetch(`/api/toggle-read/${id}/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'mark_read' })
            })
                .then(() => {
                    // Navigate after marking as read
                    if (url) window.location.href = url;
                })
                .catch(error => {
                    console.error('Mark read error:', error);
                    // Navigate anyway
                    if (url) window.location.href = url;
                });
        } else {
            // Guest
            addToSeen(id);
            element.classList.remove('blink-red');
            const toggle = element.querySelector('.blink-toggle');
            if (toggle) toggle.checked = true;

            // Navigate
            if (url) window.location.href = url;
        }
    };
});
