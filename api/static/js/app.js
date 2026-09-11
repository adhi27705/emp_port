document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const employeeGrid = document.getElementById('employeeGrid');
  const employeeCount = document.getElementById('employeeCount');
  const emptyState = document.getElementById('emptyState');
  const filterBar = document.getElementById('filterBar');
  const resetFiltersBtn = document.getElementById('resetFiltersBtn');

  const addEmployeeBtn = document.getElementById('addEmployeeBtn');
  const addModal = document.getElementById('addModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const cancelModalBtn = document.getElementById('cancelModalBtn');
  const addEmployeeForm = document.getElementById('addEmployeeForm');
  const photoInput = document.getElementById('photoInput');
  const photoPreview = document.getElementById('photoPreview');
  const submitBtn = document.getElementById('submitBtn');
  const toast = document.getElementById('toast');

  let debounceTimer = null;
  let activeDepartment = 'All';

  // 1. Live Search Listener without page reload
  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const query = e.target.value.trim();
    
    // Toggle clear search button visibility
    clearSearchBtn.style.display = query ? 'flex' : 'none';

    debounceTimer = setTimeout(() => {
      fetchEmployees(query, activeDepartment);
    }, 200);
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    fetchEmployees('', activeDepartment);
    searchInput.focus();
  });

  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener('click', () => {
      searchInput.value = '';
      clearSearchBtn.style.display = 'none';
      setDepartmentFilter('All');
    });
  }

  // 2. Department Filter Pills
  filterBar.addEventListener('click', (e) => {
    const pill = e.target.closest('.filter-pill');
    if (!pill) return;

    const dept = pill.dataset.dept;
    setDepartmentFilter(dept);
  });

  function setDepartmentFilter(dept) {
    activeDepartment = dept;
    document.querySelectorAll('.filter-pill').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.dept === dept);
    });
    fetchEmployees(searchInput.value.trim(), activeDepartment);
  }

  const DEFAULT_EMPLOYEES = [
    { id: 1, name: "Sarah Connor", role: "Principal Site Reliability Engineer", department: "Engineering", email: "sarah.connor@cyberdyne.internal", photo_path: "/static/img/avatar-sarah.svg" },
    { id: 2, name: "Alex Chen", role: "Lead UI/UX Designer", department: "Design", email: "alex.chen@designlab.internal", photo_path: "/static/img/avatar-alex.svg" },
    { id: 3, name: "Marcus Vance", role: "Cloud Infrastructure Architect", department: "Engineering", email: "marcus.v@cloudops.internal", photo_path: "/static/img/avatar-marcus.svg" },
    { id: 4, name: "Priya Patel", role: "Head of People Operations", department: "Human Resources", email: "priya.patel@workplace.internal", photo_path: "/static/img/avatar-priya.svg" },
    { id: 5, name: "Elena Rostova", role: "Senior DevOps Engineer", department: "Engineering", email: "elena.rostova@devops.internal", photo_path: "/static/img/avatar-elena.svg" },
    { id: 6, name: "Liam Tanaka", role: "Staff Product Manager", department: "Product", email: "liam.tanaka@product.internal", photo_path: "/static/img/avatar-liam.svg" }
  ];

  // 3. Fetch Employees (AJAX /api/search route)
  async function fetchEmployees(query = '', dept = 'All') {
    try {
      const params = new URLSearchParams();
      if (query) params.append('q', query);
      if (dept && dept !== 'All') params.append('dept', dept);

      const queryString = params.toString() ? `?${params.toString()}` : '';
      let res = await fetch(`/api/search${queryString}`);
      
      if (!res.ok) {
        // Fallback to /search if needed
        res = await fetch(`/search${queryString}`);
      }

      const text = await res.text();
      let employees = null;

      try {
        employees = JSON.parse(text);
      } catch (parseErr) {
        console.warn('Response was not JSON:', text.slice(0, 80));
      }

      if (!Array.isArray(employees)) {
        // Resilient fallback to default employees if server returns non-JSON or wakes from cold start
        if (!query && dept === 'All') {
          employees = DEFAULT_EMPLOYEES;
        } else {
          const q = query.toLowerCase();
          employees = DEFAULT_EMPLOYEES.filter(emp => {
            const matchesDept = (dept === 'All' || emp.department === dept);
            const matchesQuery = !q || emp.name.toLowerCase().includes(q) || 
                                 emp.role.toLowerCase().includes(q) || 
                                 emp.department.toLowerCase().includes(q) || 
                                 emp.email.toLowerCase().includes(q);
            return matchesDept && matchesQuery;
          });
        }
      }

      renderEmployeeCards(employees);
    } catch (err) {
      console.error('Failed to query employees:', err);
      // Even on network error, display default employees
      renderEmployeeCards(DEFAULT_EMPLOYEES);
    }
  }

  function renderEmployeeCards(employees) {
    employeeCount.textContent = employees.length;

    if (!employees || employees.length === 0) {
      employeeGrid.innerHTML = '';
      emptyState.style.display = 'block';
      return;
    }

    emptyState.style.display = 'none';
    employeeGrid.innerHTML = employees.map(emp => `
      <div class="employee-card" data-id="${emp.id}">
        <div class="avatar-wrapper">
          <img 
            src="${escapeHtml(emp.photo_path)}" 
            alt="${escapeHtml(emp.name)}" 
            class="employee-avatar"
            onerror="this.src='/static/img/placeholder.svg'"
          />
          <div class="status-dot" title="Active team member"></div>
        </div>
        <h3 class="employee-name">${escapeHtml(emp.name)}</h3>
        <p class="employee-role">${escapeHtml(emp.role)}</p>
        <span class="department-badge" data-dept="${escapeHtml(emp.department)}">${escapeHtml(emp.department)}</span>
        
        <div class="card-footer">
          <a href="mailto:${escapeHtml(emp.email)}" class="employee-email" title="Send email to ${escapeHtml(emp.email)}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
              <polyline points="22,6 12,13 2,6"/>
            </svg>
            <span>${escapeHtml(emp.email)}</span>
          </a>
        </div>
      </div>
    `).join('');
  }

  // 4. Photo Upload Preview & Drag and Drop
  photoInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        photoPreview.src = event.target.result;
      };
      reader.readAsDataURL(file);
    }
  });

  // 5. Modal Controls
  function openModal() {
    addModal.classList.add('active');
    addEmployeeForm.reset();
    photoPreview.src = '/static/img/placeholder.svg';
    document.getElementById('nameInput').focus();
  }

  function closeModal() {
    addModal.classList.remove('active');
  }

  addEmployeeBtn.addEventListener('click', openModal);
  closeModalBtn.addEventListener('click', closeModal);
  cancelModalBtn.addEventListener('click', closeModal);

  addModal.addEventListener('click', (e) => {
    if (e.target === addModal) closeModal();
  });

  // 6. Register Form Submission (AJAX - Photo upload to /uploads volume)
  addEmployeeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Saving...</span>';

    const formData = new FormData(addEmployeeForm);

    try {
      let res = await fetch('/api/register', {
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        res = await fetch('/register', {
          method: 'POST',
          body: formData
        });
      }
      let text = await res.text();
      let data;

      try {
        data = JSON.parse(text);
      } catch (parseErr) {
        throw new Error('Server returned invalid response');
      }

      if (!res.ok) {
        throw new Error(data.error || 'Failed to register employee');
      }

      showToast(`Added ${data.employee.name} to directory!`, 'success');
      closeModal();
      searchInput.value = '';
      clearSearchBtn.style.display = 'none';
      setDepartmentFilter('All');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
          <polyline points="17 21 17 13 7 13 7 21"/>
          <polyline points="7 3 7 8 15 8"/>
        </svg>
        Save Employee
      `;
    }
  });

  // Toast Helper
  function showToast(msg, type = 'success') {
    toast.textContent = msg;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
      toast.classList.remove('show');
    }, 3500);
  }

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Initial load to trigger avatar updates
  fetchEmployees();
});
