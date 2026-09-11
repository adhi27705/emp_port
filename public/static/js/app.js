document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements - Directory & Search
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const employeeGrid = document.getElementById('employeeGrid');
  const employeeCount = document.getElementById('employeeCount');
  const emptyState = document.getElementById('emptyState');
  const filterBar = document.getElementById('filterBar');
  const resetFiltersBtn = document.getElementById('resetFiltersBtn');

  // DOM Elements - Add Employee Modal
  const addEmployeeBtn = document.getElementById('addEmployeeBtn');
  const addModal = document.getElementById('addModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const cancelModalBtn = document.getElementById('cancelModalBtn');
  const addEmployeeForm = document.getElementById('addEmployeeForm');
  const photoInput = document.getElementById('photoInput');
  const photoPreview = document.getElementById('photoPreview');
  const submitBtn = document.getElementById('submitBtn');
  const toast = document.getElementById('toast');

  // DOM Elements - Authentication & Header
  const loginBtn = document.getElementById('loginBtn');
  const userProfile = document.getElementById('userProfile');
  const adminName = document.getElementById('adminName');
  const logoutBtn = document.getElementById('logoutBtn');

  // DOM Elements - Login Modal
  const loginModal = document.getElementById('loginModal');
  const closeLoginModalBtn = document.getElementById('closeLoginModalBtn');
  const cancelLoginBtn = document.getElementById('cancelLoginBtn');
  const loginForm = document.getElementById('loginForm');
  const loginUsername = document.getElementById('loginUsername');
  const loginPassword = document.getElementById('loginPassword');
  const togglePasswordBtn = document.getElementById('togglePasswordBtn');
  const fillDemoCredsBtn = document.getElementById('fillDemoCredsBtn');
  const submitLoginBtn = document.getElementById('submitLoginBtn');

  // DOM Elements - Delete Confirmation Modal
  const deleteModal = document.getElementById('deleteModal');
  const closeDeleteModalBtn = document.getElementById('closeDeleteModalBtn');
  const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
  const deleteEmployeeName = document.getElementById('deleteEmployeeName');

  let debounceTimer = null;
  let activeDepartment = 'All';
  let pendingDeleteId = null;
  let currentEmployees = [];

  // =========================================================================
  // Authentication State Management
  // =========================================================================
  function getAuthToken() {
    return localStorage.getItem('auth_token');
  }

  function getAuthUser() {
    try {
      return JSON.parse(localStorage.getItem('auth_user') || 'null');
    } catch {
      return null;
    }
  }

  function isAuthenticated() {
    const token = getAuthToken();
    return Boolean(token && token.startsWith('admin-token-'));
  }

  function setAuth(token, user) {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('auth_user', JSON.stringify(user));
    updateAuthUI();
  }

  function clearAuth() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    updateAuthUI();
  }

  function updateAuthUI() {
    const authed = isAuthenticated();
    const user = getAuthUser();

    if (authed) {
      if (loginBtn) loginBtn.style.display = 'none';
      if (userProfile) {
        userProfile.style.display = 'flex';
        if (adminName && user) {
          adminName.textContent = user.username || 'Admin';
        }
      }
    } else {
      if (loginBtn) loginBtn.style.display = 'flex';
      if (userProfile) userProfile.style.display = 'none';
    }
  }

  // Initialize Auth state on load
  updateAuthUI();

  // =========================================================================
  // 1. Live Search Listener without page reload
  // =========================================================================
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

  // =========================================================================
  // 2. Department Filter Pills
  // =========================================================================
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

  // =========================================================================
  // 3. Fetch Employees (AJAX /api/search route)
  // =========================================================================
  async function fetchEmployees(query = '', dept = 'All') {
    try {
      const params = new URLSearchParams();
      if (query) params.append('q', query);
      if (dept && dept !== 'All') params.append('dept', dept);

      const queryString = params.toString() ? `?${params.toString()}` : '';
      let res = await fetch(`/api/search${queryString}`);
      
      if (!res.ok) {
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

      currentEmployees = employees;
      renderEmployeeCards(employees);
    } catch (err) {
      console.error('Failed to query employees:', err);
      currentEmployees = DEFAULT_EMPLOYEES;
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
        <!-- Delete Button Action -->
        <div class="card-header-actions">
          <button 
            class="btn-card-delete" 
            data-id="${emp.id}" 
            data-name="${escapeHtml(emp.name)}" 
            title="Delete ${escapeHtml(emp.name)}" 
            type="button"
            aria-label="Delete employee ${escapeHtml(emp.name)}"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>

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

  // =========================================================================
  // 4. Employee Deletion Workflow
  // =========================================================================
  employeeGrid.addEventListener('click', (e) => {
    const deleteBtn = e.target.closest('.btn-card-delete');
    if (!deleteBtn) return;

    const empId = deleteBtn.dataset.id;
    const empName = deleteBtn.dataset.name;

    if (!isAuthenticated()) {
      showToast('Please sign in as Administrator to delete employee records.', 'error');
      openLoginModal();
      return;
    }

    pendingDeleteId = empId;
    if (deleteEmployeeName) {
      deleteEmployeeName.textContent = empName || 'this employee';
    }
    openDeleteModal();
  });

  function openDeleteModal() {
    if (deleteModal) deleteModal.classList.add('active');
  }

  function closeDeleteModal() {
    if (deleteModal) deleteModal.classList.remove('active');
    pendingDeleteId = null;
  }

  if (closeDeleteModalBtn) closeDeleteModalBtn.addEventListener('click', closeDeleteModal);
  if (cancelDeleteBtn) cancelDeleteBtn.addEventListener('click', closeDeleteModal);
  if (deleteModal) {
    deleteModal.addEventListener('click', (e) => {
      if (e.target === deleteModal) closeDeleteModal();
    });
  }

  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', async () => {
      if (!pendingDeleteId) return;

      confirmDeleteBtn.disabled = true;
      confirmDeleteBtn.innerHTML = '<span>Deleting...</span>';

      const token = getAuthToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      try {
        let res = await fetch('/api/delete', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ id: pendingDeleteId })
        });

        if (!res.ok) {
          res = await fetch(`/api/delete/${pendingDeleteId}`, {
            method: 'DELETE',
            headers: headers
          });
        }

        if (!res.ok) {
          res = await fetch(`/delete/${pendingDeleteId}`, {
            method: 'DELETE',
            headers: headers
          });
        }

        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.error || 'Failed to delete employee record.');
        }

        // Animate card removal
        const cardElem = document.querySelector(`.employee-card[data-id="${pendingDeleteId}"]`);
        if (cardElem) {
          cardElem.classList.add('removing');
          setTimeout(() => {
            cardElem.remove();
            // Update local memory list
            currentEmployees = currentEmployees.filter(emp => String(emp.id) !== String(pendingDeleteId));
            employeeCount.textContent = currentEmployees.length;
            if (currentEmployees.length === 0) {
              emptyState.style.display = 'block';
            }
          }, 350);
        }

        showToast(data.message || 'Employee deleted successfully.', 'success');
        closeDeleteModal();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          <span>Delete Employee</span>
        `;
      }
    });
  }

  // =========================================================================
  // 5. Admin Login & Logout Workflow
  // =========================================================================
  function openLoginModal() {
    if (loginModal) {
      loginModal.classList.add('active');
      loginForm.reset();
      if (loginUsername) loginUsername.focus();
    }
  }

  function closeLoginModal() {
    if (loginModal) loginModal.classList.remove('active');
  }

  if (loginBtn) loginBtn.addEventListener('click', openLoginModal);
  if (closeLoginModalBtn) closeLoginModalBtn.addEventListener('click', closeLoginModal);
  if (cancelLoginBtn) cancelLoginBtn.addEventListener('click', closeLoginModal);
  if (loginModal) {
    loginModal.addEventListener('click', (e) => {
      if (e.target === loginModal) closeLoginModal();
    });
  }

  // Quick fill demo credentials
  if (fillDemoCredsBtn) {
    fillDemoCredsBtn.addEventListener('click', () => {
      if (loginUsername) loginUsername.value = 'admin';
      if (loginPassword) loginPassword.value = 'admin123';
      if (submitLoginBtn) submitLoginBtn.focus();
    });
  }

  // Toggle password visibility
  if (togglePasswordBtn && loginPassword) {
    togglePasswordBtn.addEventListener('click', () => {
      const isPassword = loginPassword.type === 'password';
      loginPassword.type = isPassword ? 'text' : 'password';
      togglePasswordBtn.innerHTML = isPassword ? `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
          <line x1="1" y1="1" x2="23" y2="23"/>
        </svg>
      ` : `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      `;
    });
  }

  // Login form submit
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      submitLoginBtn.disabled = true;
      submitLoginBtn.innerHTML = '<span>Signing In...</span>';

      const username = loginUsername.value.trim();
      const password = loginPassword.value.trim();

      try {
        let res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
          res = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
          });
        }

        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
          throw new Error(data.error || 'Invalid username or password.');
        }

        setAuth(data.token, data.user);
        closeLoginModal();
        showToast('Signed in successfully as Administrator!', 'success');
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        submitLoginBtn.disabled = false;
        submitLoginBtn.innerHTML = '<span>Sign In</span>';
      }
    });
  }

  // Logout handler
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      try {
        await fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
      } catch {}
      clearAuth();
      showToast('Logged out successfully.', 'success');
    });
  }

  // =========================================================================
  // 6. Photo Upload Preview & Drag and Drop
  // =========================================================================
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

  // =========================================================================
  // 7. Add Employee Modal Controls
  // =========================================================================
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

  // =========================================================================
  // 8. Register Form Submission (AJAX - Photo upload to /uploads volume)
  // =========================================================================
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

  // Initial load to populate cards
  fetchEmployees();
});
