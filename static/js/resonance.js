// static/js/resonance.js
// Единый обработчик реакций для всего сайта

(function() {
    // Универсальная функция для обновления UI
    function updateReactionUI(impulseId, type, data) {
        // Ищем все кнопки с этим impulseId на странице
        const buttons = document.querySelectorAll(`.reaction-btn[data-impulse-id="${impulseId}"][data-type="${type}"]`);

        buttons.forEach(btn => {
            const countSpan = btn.querySelector('.reaction-count');
            if (countSpan) {
                const newCount = type === 'heart' ? data.heart_count : data.blast_count;
                // ВСЕГДА формат [ число ]
                countSpan.innerText = `[${newCount}]`;
            }

            // Обновляем активное состояние
            const isActive = type === 'heart' ? data.user_heart : data.user_blast;
            if (isActive !== undefined) {
                if (isActive) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            }
        });
    }

    // Обработчик клика
    async function resonanceHandler(e) {
        e.preventDefault();
        e.stopPropagation();

        const btn = e.currentTarget;
        const impulseId = btn.dataset.impulseId;
        const type = btn.dataset.type;

        if (!impulseId || !type) {
            console.error('Missing impulseId or type');
            return;
        }

        try {
            const response = await fetch('/api/resonate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrftoken
                },
                credentials: 'same-origin',
                body: `impulse_id=${impulseId}&resonance_type=${type}`
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            updateReactionUI(impulseId, type, data);

        } catch (error) {
            console.error('Resonance error:', error);
        }
    }

    // Инициализация всех кнопок на странице
    function initAllReactions() {
        const buttons = document.querySelectorAll('.reaction-btn');
        buttons.forEach(btn => {
            btn.removeEventListener('click', resonanceHandler);
            btn.addEventListener('click', resonanceHandler);
        });
    }

    // Наблюдатель за новыми элементами
    const observer = new MutationObserver(function(mutations) {
        let shouldInit = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        if (node.querySelector && node.querySelector('.reaction-btn')) {
                            shouldInit = true;
                        }
                    }
                });
            }
        });
        if (shouldInit) {
            initAllReactions();
        }
    });

    // Запуск при загрузке
    document.addEventListener('DOMContentLoaded', function() {
        initAllReactions();
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
})();