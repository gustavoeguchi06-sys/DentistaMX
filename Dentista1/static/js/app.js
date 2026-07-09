(function () {
  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.querySelector('.sidebar-backdrop');
  const menuLinks = document.querySelectorAll('.menu a');

  if (!toggle || !sidebar) return;

  const closeSidebar = () => {
    sidebar.classList.remove('open');
    document.body.classList.remove('sidebar-open');
  };

  const openSidebar = () => {
    sidebar.classList.add('open');
    document.body.classList.add('sidebar-open');
  };

  toggle.addEventListener('click', function (event) {
    event.stopPropagation();
    if (sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }

  menuLinks.forEach((link) => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 900) {
        closeSidebar();
      }
    });
  });

  const path = window.location.pathname.replace(/\/+$/, '');
  menuLinks.forEach((link) => {
    try {
      const href = new URL(link.href).pathname.replace(/\/+$/, '');
      if (href === path) {
        link.classList.add('active');
      }
    } catch (error) {
      // ignore invalid URLs
    }
  });

  document.addEventListener('click', (event) => {
    if (window.innerWidth <= 900 && sidebar.classList.contains('open')) {
      const clickInside = sidebar.contains(event.target) || toggle.contains(event.target);
      if (!clickInside) {
        closeSidebar();
      }
    }
  });

  const dateInputs = document.querySelectorAll('input.mask-date');
  dateInputs.forEach((input) => {
    const formatDateValue = (raw) => {
      const digits = raw.replace(/\D/g, '').slice(0, 8);
      if (digits.length <= 2) {
        return digits;
      }
      if (digits.length <= 4) {
        return `${digits.slice(0, 2)}/${digits.slice(2)}`;
      }
      return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)}`;
    };

    input.addEventListener('input', () => {
      const previousValue = input.value;
      input.value = formatDateValue(previousValue);
    });

    input.addEventListener('paste', (event) => {
      event.preventDefault();
      const pasted = (event.clipboardData || window.clipboardData).getData('text');
      input.value = formatDateValue(pasted);
    });

    input.addEventListener('blur', () => {
      const valid = /^\d{2}\/\d{2}\/\d{4}$/.test(input.value);
      if (input.value && !valid) {
        input.setCustomValidity('Use o formato dd/mm/aaaa');
      } else {
        input.setCustomValidity('');
      }
    });
  });

  const datetimeInputs = document.querySelectorAll('input.mask-datetime');
  datetimeInputs.forEach((input) => {
    const formatDateTimeValue = (raw) => {
      const digits = raw.replace(/\D/g, '').slice(0, 12);
      if (digits.length <= 2) {
        return digits;
      }
      if (digits.length <= 4) {
        return `${digits.slice(0, 2)}/${digits.slice(2)}`;
      }
      if (digits.length <= 8) {
        return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
      }
      if (digits.length <= 10) {
        return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)} ${digits.slice(8)}`;
      }
      return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)} ${digits.slice(8, 10)}:${digits.slice(10, 12)}`;
    };

    input.addEventListener('input', () => {
      const previousValue = input.value;
      input.value = formatDateTimeValue(previousValue);
    });

    input.addEventListener('paste', (event) => {
      event.preventDefault();
      const pasted = (event.clipboardData || window.clipboardData).getData('text');
      input.value = formatDateTimeValue(pasted);
    });

    input.addEventListener('blur', () => {
      const valid = /^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}$/.test(input.value);
      if (input.value && !valid) {
        input.setCustomValidity('Use o formato dd/mm/aaaa hh:mm');
      } else {
        input.setCustomValidity('');
      }
    });
  });
})();
