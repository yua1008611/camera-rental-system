function calculateRentalAmount() {
    const cameraSelect = document.querySelector("#cameraSelect");
    const startInput = document.querySelector("#startDate");
    const endInput = document.querySelector("#endDate");
    const daysInput = document.querySelector("#rentalDays");
    const amountInput = document.querySelector("#amountDue");

    if (!cameraSelect || !startInput || !endInput || !daysInput || !amountInput) {
        return;
    }

    const selected = cameraSelect.options[cameraSelect.selectedIndex];
    const dailyPrice = Number(selected?.dataset.price || 0);
    const startDate = new Date(startInput.value);
    const endDate = new Date(endInput.value);

    if (!dailyPrice || Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
        daysInput.value = "";
        amountInput.value = "0.00";
        return;
    }

    const oneDay = 24 * 60 * 60 * 1000;
    const days = Math.floor((endDate - startDate) / oneDay) + 1;
    if (days <= 0) {
        daysInput.value = "日期错误";
        amountInput.value = "0.00";
        return;
    }

    daysInput.value = days;
    amountInput.value = (days * dailyPrice).toFixed(2);
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    ["#cameraSelect", "#startDate", "#endDate"].forEach((selector) => {
        const element = document.querySelector(selector);
        if (element) {
            element.addEventListener("change", calculateRentalAmount);
        }
    });
    calculateRentalAmount();
});
