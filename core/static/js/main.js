document.addEventListener("DOMContentLoaded", function () {

    // ── Sidebar toggle ──────────────────────────────────────────────────
    const appShell     = document.getElementById("app-shell");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const COLLAPSED_KEY = "sidebar_collapsed";

    // Note: the collapsed state is restored by an inline pre-paint script in
    // base.html so that navigating between pages does not re-animate the
    // minimize transition. The toggle handler below only persists changes.

    // Inject backdrop for mobile if not present
    if (!document.getElementById("sidebarBackdrop")) {
        const backdrop = document.createElement("div");
        backdrop.className = "sidebar-backdrop";
        backdrop.id = "sidebarBackdrop";
        appShell.appendChild(backdrop);
        backdrop.addEventListener("click", closeMobileSidebar);
    }

    function closeMobileSidebar() {
        appShell.classList.remove("sidebar-open");
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            if (window.innerWidth <= 1024) {
                appShell.classList.toggle("sidebar-open");
            } else {
                const collapsed = appShell.classList.toggle("sidebar-collapsed");
                localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
            }
        });
    }

    // Close mobile sidebar on nav link click
    document.querySelectorAll(".sidebar-link").forEach(link => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 1024) closeMobileSidebar();
        });
    });

    // ── Dropdowns ──────────────────────────────────────────────────────
    function setupDropdown(toggleId, panelId) {
        const toggle = document.getElementById(toggleId);
        const panel  = document.getElementById(panelId);
        if (!toggle || !panel) return;
        toggle.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = !panel.classList.contains("hidden");
            document.querySelectorAll(".dropdown-panel").forEach(p => p.classList.add("hidden"));
            panel.classList.toggle("hidden", isOpen);
        });
    }
    setupDropdown("notifBellToggle", "notificationDropdown");
    setupDropdown("userMenuToggle",  "userDropdown");
    document.addEventListener("click", () => {
        document.querySelectorAll(".dropdown-panel").forEach(p => p.classList.add("hidden"));
    });

    // ── Modals ─────────────────────────────────────────────────────────
    document.querySelectorAll("[data-modal-target]").forEach(btn => {
        btn.addEventListener("click", function () {
            const modal = document.getElementById(this.dataset.modalTarget);
            if (modal) modal.classList.add("active");
        });
    });
    document.querySelectorAll("[data-modal-close]").forEach(btn => {
        btn.addEventListener("click", function () {
            const modal = document.getElementById(this.dataset.modalClose);
            if (modal) modal.classList.remove("active");
        });
    });
    document.querySelectorAll(".modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) overlay.classList.remove("active");
        });
    });

    // ── File upload ────────────────────────────────────────────────────
    document.querySelectorAll(".file-upload").forEach(upload => {
        const input   = upload.querySelector('input[type="file"]');
        const display = upload.parentElement.querySelector(".file-upload-filename");
        if (!input) return;

        upload.addEventListener("click", () => input.click());
        upload.addEventListener("dragover", e => { e.preventDefault(); upload.classList.add("dragover"); });
        upload.addEventListener("dragleave", () => upload.classList.remove("dragover"));
        upload.addEventListener("drop", e => {
            e.preventDefault();
            upload.classList.remove("dragover");
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                showFilename(e.dataTransfer.files[0].name);
            }
        });
        input.addEventListener("change", () => {
            if (input.files.length) showFilename(input.files[0].name);
        });
        function showFilename(name) {
            if (display) {
                display.classList.remove("hidden");
                const span = display.querySelector("span");
                if (span) span.textContent = name;
            }
        }
    });

    // ── Live auto-refresh (tables & notification badge) ────────────────
    // Refresh notification badge every 4 seconds
    function refreshNotifBadge() {
        fetch("/notifications/unread-count/")
            .then(r => r.json())
            .then(data => {
                const dot         = document.querySelector(".topbar-icon-btn .badge-dot");
                const sidebarBadge = document.querySelector(".sidebar-link[href*='notifications'] .sidebar-link-badge");
                const count = data.unread_count;
                if (dot)          dot.style.display          = count > 0 ? "block" : "none";
                if (sidebarBadge) {
                    sidebarBadge.textContent    = count;
                    sidebarBadge.style.display  = count > 0 ? "inline-flex" : "none";
                }
            })
            .catch(() => {});
    }

    if (document.getElementById("notifBellToggle")) {
        setInterval(refreshNotifBadge, 4000);
    }

    // Auto-reload list pages every 5 seconds (non-intrusively)
    // Only on list/dashboard pages, not on forms or detail pages
    const isListPage = document.querySelector("[data-auto-refresh]");
    if (isListPage) {
        const interval = parseInt(isListPage.dataset.autoRefresh || "5000");
        setInterval(() => {
            // Only reload if no modal is open and no input is focused
            const modalOpen   = document.querySelector(".modal-overlay.active");
            const inputFocused = document.activeElement &&
                ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);
            if (!modalOpen && !inputFocused) {
                // Soft reload: re-fetch current URL and replace main content only
                fetch(window.location.href, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                    .then(r => r.text())
                    .then(html => {
                        const parser  = new DOMParser();
                        const newDoc  = parser.parseFromString(html, "text/html");
                        const newContent = newDoc.querySelector(".page-content");
                        const curContent = document.querySelector(".page-content");
                        if (newContent && curContent) {
                            curContent.innerHTML = newContent.innerHTML;
                            // Re-init modal/dropdown handlers on new content
                            reinitHandlers();
                        }
                    })
                    .catch(() => {});
            }
        }, interval);
    }

    function reinitHandlers() {
        // Re-attach modal open
        document.querySelectorAll("[data-modal-target]").forEach(btn => {
            btn.addEventListener("click", function () {
                const modal = document.getElementById(this.dataset.modalTarget);
                if (modal) modal.classList.add("active");
            });
        });
        // Re-attach modal close
        document.querySelectorAll("[data-modal-close]").forEach(btn => {
            btn.addEventListener("click", function () {
                const modal = document.getElementById(this.dataset.modalClose);
                if (modal) modal.classList.remove("active");
            });
        });
    }

    // ── Live search (debounced, no page reload) ───────────────────────
    const searchInputs = document.querySelectorAll(".search-bar input[name='q']");
    searchInputs.forEach(input => {
        let debounceTimer;
        input.addEventListener("input", function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const form = input.closest("form");
                if (form) {
                    const url    = new URL(window.location.href);
                    const params = new URLSearchParams(new FormData(form));
                    params.forEach((v, k) => url.searchParams.set(k, v));
                    if (!input.value) url.searchParams.delete("q");
                    // Push state without reload
                    history.replaceState(null, "", url.toString());
                    // Fetch and replace table
                    fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
                        .then(r => r.text())
                        .then(html => {
                            const parser     = new DOMParser();
                            const newDoc     = parser.parseFromString(html, "text/html");
                            const newContent = newDoc.querySelector(".page-content");
                            const curContent = document.querySelector(".page-content");
                            if (newContent && curContent) {
                                curContent.innerHTML = newContent.innerHTML;
                                reinitHandlers();
                            }
                        })
                        .catch(() => {});
                }
            }, 350);
        });
    });

    // ── Status filter tabs — live filter without full reload ──────────
    document.querySelectorAll(".status-tab").forEach(tab => {
        tab.addEventListener("click", function (e) {
            e.preventDefault();
            const url = new URL(this.href, window.location.origin);
            history.pushState(null, "", url.toString());
            fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(r => r.text())
                .then(html => {
                    const parser     = new DOMParser();
                    const newDoc     = parser.parseFromString(html, "text/html");
                    const newContent = newDoc.querySelector(".page-content");
                    const curContent = document.querySelector(".page-content");
                    if (newContent && curContent) {
                        curContent.innerHTML = newContent.innerHTML;
                        reinitHandlers();
                    }
                })
                .catch(() => {});
        });
    });

    // Handle browser back/forward
    window.addEventListener("popstate", () => {
        fetch(window.location.href, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(r => r.text())
            .then(html => {
                const parser     = new DOMParser();
                const newDoc     = parser.parseFromString(html, "text/html");
                const newContent = newDoc.querySelector(".page-content");
                const curContent = document.querySelector(".page-content");
                if (newContent && curContent) {
                    curContent.innerHTML = newContent.innerHTML;
                    reinitHandlers();
                }
            })
            .catch(() => {});
    });

});
