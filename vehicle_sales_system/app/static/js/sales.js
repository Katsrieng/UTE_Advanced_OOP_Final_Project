(() => {
  const form = document.querySelector('#sale-form');
  if (!form) return;
  let step = 1;
  let submitting = false;
  const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  const chosen = name => form.querySelector(`input[name="${name}"]:checked`);
  const panels = [...form.querySelectorAll('[data-step]')];
  const discount = document.querySelector('#discount');
  const error = message => { panels[step-1].querySelector('.step-error').textContent = message; };
  function showStep(next) {
    step = next;
    panels.forEach(panel => { panel.hidden = Number(panel.dataset.step) !== step; });
    document.querySelectorAll('.stepper li').forEach((item, index) => {
      item.classList.toggle('active', index+1 === step); item.classList.toggle('complete', index+1 < step);
      if (index+1 === step) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
    });
    error('');
    const heading = panels[step-1].querySelector('h2'); heading.tabIndex = -1; heading.focus();
    if (step === 3) review();
  }
  function review() {
    const customer = chosen('customer_id'), vehicle = chosen('vehicle_id');
    document.querySelector('#review-customer').textContent = customer.dataset.name;
    document.querySelector('#review-email').textContent = customer.dataset.email;
    document.querySelector('#review-vehicle').textContent = vehicle.dataset.name;
    document.querySelector('#review-vin').textContent = vehicle.dataset.vin;
    document.querySelector('#review-price').textContent = money(Number(vehicle.dataset.price));
    discount.max = vehicle.dataset.price;
    document.querySelector('#review-total').textContent = money(Number(vehicle.dataset.price) - Number(discount.value));
  }
  form.querySelectorAll('[data-next]').forEach(button => button.addEventListener('click', () => {
    if (!chosen(step === 1 ? 'customer_id' : 'vehicle_id')) { error(`Select a ${step === 1 ? 'customer' : 'vehicle'} to continue.`); return; }
    showStep(step+1);
  }));
  form.querySelectorAll('[data-back]').forEach(button => button.addEventListener('click', () => showStep(step-1)));
  discount.addEventListener('input', () => { review(); error(discount.validity.valid ? '' : 'Enter a discount between zero and the selling price.'); });
  [['customer', '.customer-option'], ['vehicle', '.vehicle-option']].forEach(([name, selector]) => {
    document.querySelector(`#${name}-search`).addEventListener('input', event => {
      let visible = 0;
      form.querySelectorAll(selector).forEach(card => { card.hidden = !card.dataset.search.includes(event.target.value.trim().toLowerCase()); if (!card.hidden) visible++; });
      document.querySelector(`#${name}-empty`).hidden = visible > 0;
    });
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submitting) return;
    if (step < 3) { panels[step-1].querySelector('[data-next]').click(); return; }
    if (!discount.reportValidity()) return;
    if (!await window.confirmAction('Complete this sale? The vehicle will be marked Sold, a stock-out movement will be recorded, and one invoice will be generated.')) return;
    submitting = true;
    const button = document.querySelector('#complete-sale'); button.disabled = true; button.classList.add('loading'); button.setAttribute('aria-busy', 'true');
    HTMLFormElement.prototype.submit.call(form);
  });
})();
