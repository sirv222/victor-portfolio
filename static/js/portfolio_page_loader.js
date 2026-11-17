
(() => {
    const loader = document.getElementById("page-loader");

    if (!loader) return;

    let isHidden = false;

    function hideLoader() {
        if (isHidden) return;

        isHidden = true;
        loader.classList.add("hidden");

        setTimeout(() => {
            loader.remove();
        }, 750);
    }

    if (document.readyState === "complete") {
        hideLoader();
    } else {
        window.addEventListener("load", hideLoader, {
            once: true
        });
    }

    window.addEventListener("pageshow", (event) => {
        if (event.persisted) {
            hideLoader();
        }
    });

})();
