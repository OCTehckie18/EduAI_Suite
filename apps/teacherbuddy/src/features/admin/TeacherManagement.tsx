import React, { useEffect, useState } from "react";
import {
  Users,
  Search,
  Plus,
  Trash2,
  Edit,
  Loader2,
  Check,
  X,
  Download,
  Upload,
  AlertTriangle
} from "lucide-react";
import { API_ENDPOINTS } from "../../shared/utils/apiConfig";

interface Teacher {
  id: number;
  name: string;
  email: string;
  role: string;
  status: string;
  department?: string | null;
  employee_id?: string | null;
  picture?: string | null;
}

interface BulkUploadResult {
  processed: number;
  successful: number;
  failed: number;
  errors: string[];
}

export const TeacherManagement: React.FC = () => {
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    search: "",
    department: "",
    status: ""
  });
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 10,
    total: 0,
    pages: 0
  });
  const [selectedTeacher, setSelectedTeacher] = useState<Teacher | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    department: "",
    employee_id: ""
  });
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState<BulkUploadResult | null>(null);

  // Fetch teachers with filters and pagination
  const fetchTeachers = async () => {
    setLoading(true);
    setError(null);

    try {
      const storedToken = localStorage.getItem("token");
      const queryParams = new URLSearchParams({
        page: pagination.page.toString(),
        limit: pagination.limit.toString(),
        search: filters.search,
        department: filters.department || undefined,
        status: filters.status || undefined
      }).toString();

      const res = await fetch(`${API_ENDPOINTS.BASE}/admin/teachers?${queryParams}`, {
        headers: {
          Authorization: `Bearer ${storedToken}`,
        },
      });

      if (res.ok) {
        const data = await res.json();
        setTeachers(data.users);
        setPagination(prev => ({
          ...prev,
          total: data.total,
          pages: Math.ceil(data.total / pagination.limit)
        }));
      } else {
        throw new Error("Failed to fetch teachers");
      }
    } catch (err) {
      console.error("Failed to fetch teachers", err);
      setError("Failed to load teachers. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Handle form submission
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError(null);

    try {
      const storedToken = localStorage.getItem("token");

      if (formMode === 'create') {
        const res = await fetch(`${API_ENDPOINTS.BASE}/admin/teachers`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${storedToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        });

        if (!res.ok) throw new Error("Failed to create teacher");
      } else {
        if (!selectedTeacher) throw new Error("No teacher selected for edit");

        const res = await fetch(`${API_ENDPOINTS.BASE}/admin/teachers/${selectedTeacher.id}`, {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${storedToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        });

        if (!res.ok) throw new Error("Failed to update teacher");
      }

      // Close form and refresh
      setShowForm(false);
      setFormMode('create');
      setFormData({
        name: "",
        email: "",
        department: "",
        employee_id: ""
      });
      await fetchTeachers();
    } catch (err) {
      console.error("Failed to save teacher", err);
      setFormError("Failed to save teacher. Please check your input and try again.");
    } finally {
      setFormLoading(false);
    }
  };

  // Handle delete teacher
  const handleDeleteTeacher = async (teacherId: number) => {
    if (!window.confirm("Are you sure you want to deactivate this teacher?")) return;

    try {
      const storedToken = localStorage.getItem("token");
      const res = await fetch(`${API_ENDPOINTS.BASE}/admin/teachers/${teacherId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${storedToken}`,
        },
      });

      if (!res.ok) throw new Error("Failed to deactivate teacher");

      await fetchTeachers();
    } catch (err) {
      console.error("Failed to deactivate teacher", err);
      setError("Failed to deactivate teacher. Please try again.");
    }
  };

  // Handle bulk upload
  const handleBulkUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setBulkUploading(true);
    setBulkResult(null);

    try {
      const storedToken = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_ENDPOINTS.BASE}/admin/teachers/bulk`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${storedToken}`,
        },
        body: formData,
      });

      if (!res.ok) throw new Error("Failed to upload teachers");

      const result = await res.json();
      setBulkResult(result);
      await fetchTeachers(); // Refresh teacher list
    } catch (err) {
      console.error("Failed to bulk upload teachers", err);
      setBulkResult({
        processed: 0,
        successful: 0,
        failed: 1,
        errors: [err.message || "Failed to upload teachers"]
      });
    } finally {
      setBulkUploading(false);
      e.target.value = ""; // Reset file input
    }
  };

  // Handle export
  const handleExport = async () => {
    try {
      const storedToken = localStorage.getItem("token");
      const queryParams = new URLSearchParams({
        role: "teacher",
        ...(filters.search && { search: filters.search }),
        ...(filters.department && { department: filters.department }),
        ...(filters.status && { status: filters.status })
      }).toString();

      const res = await fetch(`${API_ENDPOINTS.BASE}/admin/users/export?${queryParams}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${storedToken}`,
        },
      });

      if (!res.ok) throw new Error("Failed to export teachers");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'teachers_export.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export teachers", err);
      setError("Failed to export teachers. Please try again.");
    }
  };

  useEffect(() => {
    fetchTeachers();
  }, [pagination.page, pagination.limit, filters.search, filters.department, filters.status]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto animate-fade-in">
        <div className="space-y-6">
          {/* Header placeholder */}
          <div className="glass-card border p-6" style={{
            borderColor: "var(--color-border)",
            background: "var(--color-surface-card)"
          }}>
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Users size={20} className="text-blue-500" />
              Teacher Management
            </h2>
            <div className="h-4 bg-gray-200 rounded w-full animate-pulse"></div>
          </div>

          {/* Table placeholder */}
          <div className="glass-card border" style={{ borderColor: "var(--color-border)" }}>
            <div className="p-4 border-b" style={{ borderColor: "var(--color-border)" }}>
              <h2 className="font-bold flex items-center gap-2">
                <Users size={18} className="text-blue-500" />
                Teachers List
              </h2>
            </div>
            <div className="p-6">
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((_, i) => (
                  <div key={i} className="h-4 bg-gray-200 rounded w-full animate-pulse"></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black mb-2" style={{ fontFamily: "var(--font-display)" }}>
            Teacher Management
          </h1>
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
            Manage all teachers in the EduAI Suite system
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setFormMode('create');
              setShowForm(true);
              setFormData({
                name: "",
                email: "",
                department: "",
                employee_id: ""
              });
            }}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> Add Teacher
          </button>
          <button
            onClick={handleExport}
            className="btn btn-outline flex items-center gap-2"
          >
            <Download size={16} /> Export
          </button>
          <input
            type="file"
            accept=".csv"
            onChange={handleBulkUpload}
            className="hidden"
            id="bulk-upload-input"
          />
          <label
            htmlFor="bulk-upload-input"
            className="btn btn-outline flex items-center gap-2"
          >
            <Upload size={16} /> Bulk Upload
          </label>
        </div>
      </div>

      {/* Bulk Upload Results */}
      {bulkResult && (
        <div className="mb-6">
          <div className={`glass-card border p-4 ${
            bulkResult.failed === 0 ? 'border-green-200 bg-green-50/50' : 'border-red-200 bg-red-50/50'
          }`}>
            <div className="flex items-start gap-3">
              {bulkResult.failed === 0 ? (
                <Check size={20} className="text-green-500 mt-0.5" />
              ) : (
                <AlertTriangle size={20} className="text-red-500 mt-0.5" />
              )}
              <div>
                <h3 className="font-bold mb-1">
                  Bulk Upload Complete
                </h3>
                <p className="text-sm">
                  Processed: {bulkResult.processed} |
                  Successful: {bulkResult.successful} |
                  Failed: {bulkResult.failed}
                </p>
                {bulkResult.errors.length > 0 && (
                  <div className="mt-2 text-xs">
                    <strong>Errors:</strong>
                    <ul className="mt-1 list-disc list-inside">
                      {bulkResult.errors.map((error, idx) => (
                        <li key={idx}>{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="glass-card border p-6 mb-6" style={{
        borderColor: "var(--color-border)",
        background: "var(--color-surface-card)"
      }}>
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Search size={20} className="text-blue-500" />
          Filter Teachers
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm font-medium mb-1">Search</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => {
                setFilters(prev => ({ ...prev, search: e.target.value }));
                setPagination(prev => ({ ...prev, page: 1 })); // Reset to first page
              }}
              placeholder="Search by name or email..."
              className="w-full pl-3 pr-1 py-2 rounded-xl border outline-none text-sm focus:ring-2 focus:ring-blue-500/20"
              style={{
                borderColor: "var(--color-border)",
                background: "var(--color-bg-base)",
                color: "var(--color-text-primary)",
              }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Department</label>
            <input
              type="text"
              value={filters.department}
              onChange={(e) => {
                setFilters(prev => ({ ...prev, department: e.target.value }));
                setPagination(prev => ({ ...prev, page: 1 }));
              }}
              placeholder="Filter by department..."
              className="w-full pl-3 pr-1 py-2 rounded-xl border outline-none text-sm focus:ring-2 focus:ring-blue-500/20"
              style={{
                borderColor: "var(--color-border)",
                background: "var(--color-bg-base)",
                color: "var(--color-text-primary)",
              }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => {
                setFilters(prev => ({ ...prev, status: e.target.value }));
                setPagination(prev => ({ ...prev, page: 1 }));
              }}
              className="w-full pl-3 pr-1 py-2 rounded-xl border outline-none text-sm focus:ring-2 focus:ring-blue-500/20"
              style={{
                borderColor: "var(--color-border)",
                background: "var(--color-bg-base)",
                color: "var(--color-text-primary)",
              }}
            >
              <option value="">All Statuses</option>
              <option value="approved">Approved</option>
              <option value="pending">Pending</option>
              <option value="denied">Denied</option>
            </select>
          </div>
        </div>
      </div>

      {/* Teacher Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white/90 backdrop-blur-lg rounded-2xl p-6 w-full max-w-md mx-4 relative">
            <button
              onClick={() => setShowForm(false)}
              className="absolute top-2 right-2 text-gray-500 hover:text-gray-700"
            >
              <X size={20} />
            </button>
            <h2 className="text-xl font-bold mb-6 text-center">
              {formMode === 'create' ? 'Add New Teacher' : 'Edit Teacher'}
            </h2>
            <form onSubmit={handleFormSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  required
                  className="w-full pl-3 pr-1 py-2 rounded-xl border outline-none text-sm focus:ring-2 focus:ring-blue-500/20"
                  style={{
                    borderColor: "var(--color-border)",
                    background: "var(--color-bg-base)",
                    color: "var(--color-text-primary)",
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  required
                  className="w-full pl-3 pr-1 py-2 rounded-xl border outline-none text-sm focus:ring-2 focus:ring-blue-500/20"
                  style={{
                    borderColor: "var(--color-border)",
                    background: "var(--color-bg-base)",
                    color: "var(--color-text-primary)",
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Department</label>
                <input
                  type="text"
                  value={formData.department}
                  onChange={(e) => setFormData(prev => ({ ...prev, department: e.target.value }))}
                  className="w-full pl-3 pr-1 py-2 rounded-xl border outline-none text-sm focus:ring-2 focus:ring-blue-500/20"
                  style={{
                    borderColor: "var(--color-border)",
                    background: "var(--color-bg-base)",
                    color: "var(--color-text-primary)",
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Employee ID</label>
                <input
                  type="text"
                  value={formData.employee_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, employee_id: e.target.value }))}
                  className="w-full pl-3 pr-1 py-2 rounded-xl border outline-none text-sm focus:ring-2 focus:ring-blue-500/20"
                  style={{
                    borderColor: "var(--color-border)",
                    background: "var(--color-bg-base)",
                    color: "var(--color-text-primary)",
                  }}
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 rounded-xl border outline-none text-sm font-medium"
                  style={{
                    borderColor: "var(--color-border)",
                    background: "var(--color-bg-base)",
                    color: "var(--color-text-primary)",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:pointer-events-none"
                >
                  {formLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <span>Save Teacher</span>
                  )}
                </button>
              </div>
              {formError && (
                <div className="mt-2 p-3 bg-red-50/50 border-red-200 text-red-700 rounded-xl text-sm">
                  {formError}
                </div>
              )}
            </form>
          </div>
        </div>
      )}

      {/* Teachers Table */}
      <div className="glass-card border" style={{ borderColor: "var(--color-border)" }}>
        <div className="p-4 border-b" style={{ borderColor: "var(--color-border)" }}>
          <h2 className="font-bold flex items-center gap-2">
            <Users size={18} className="text-blue-500" />
            Teachers List ({teachers.length} of {pagination.total})
          </h2>
        </div>

        {error ? (
          <div className="p-6 text-center">
            <AlertTriangle size={32} className="mx-auto mb-4 text-red-500" />
            <p className="text-gray-500 font-semibold text-lg">Error Loading Teachers</p>
            <p className="text-sm text-gray-400">{error}</p>
            <button
              onClick={fetchTeachers}
              className="mt-4 btn btn-sm btn-primary"
            >
              Retry
            </button>
          </div>
        ) : teachers.length === 0 ? (
          <div className="p-12 text-center">
            <Users size={48} className="mx-auto mb-4 opacity-20" />
            <p className="text-gray-500 font-semibold text-lg">No Teachers Found</p>
            <p className="text-sm text-gray-400">
              Try adjusting your filters or add new teachers using the button above.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr style={{ background: "var(--color-surface-base)", borderBottom: "1px solid var(--color-border)" }}>
                  <th className="p-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Teacher</th>
                  <th className="p-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Email</th>
                  <th className="p-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Department</th>
                  <th className="p-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="p-4 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: "var(--color-border)" }}>
                {teachers.map((teacher) => (
                  <tr key={teacher.id} className="hover:bg-gray-50/5 dark:hover:bg-gray-800/20 transition-colors">
                    <td className="p-4 flex items-center gap-3">
                      {teacher.picture ? (
                        <img src={teacher.picture} alt="" className="w-10 h-10 rounded-full bg-gray-100" referrerPolicy="no-referrer" />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                          {teacher.name.charAt(0).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <p className="font-semibold text-sm">{teacher.name}</p>
                        <p className="text-xs text-gray-500">#{teacher.id}</p>
                      </div>
                    </td>
                    <td className="p-4 break-all text-sm">{teacher.email}</td>
                    <td className="p-4 text-sm">{teacher.department || 'N/A'}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 text-xs font-bold rounded uppercase ${teacher.status === "approved" ? "bg-green-100 text-green-700" : teacher.status === "pending" ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700"}`}>
                        {teacher.status}
                      </span>
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => {
                          setFormMode('edit');
                          setSelectedTeacher(teacher);
                          setFormData({
                            name: teacher.name || "",
                            email: teacher.email || "",
                            department: teacher.department || "",
                            employee_id: teacher.employee_id || ""
                          });
                          setShowForm(true);
                        }}
                        className="px-3 py-1.5 bg-blue-500 text-white rounded-lg text-xs font-bold hover:bg-blue-600 transition-colors"
                      >
                        <span className="flex items-center gap-1">
                          <Edit size={14} /> Edit
                        </span>
                      </button>
                      <button
                        onClick={() => handleDeleteTeacher(teacher.id)}
                        className="px-3 py-1.5 bg-red-100 text-red-700 rounded-lg text-xs font-bold hover:bg-red-200 transition-colors"
                      >
                        <span className="flex items-center gap-1">
                          <Trash2 size={14} /> Deactivate
                        </span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {pagination.pages > 1 && (
          <div className="p-4 flex items-center justify-between text-sm">
            <div>
              Showing
              {(pagination.page - 1) * pagination.limit + 1}-{Math.min(pagination.page * pagination.limit, pagination.total)}
              of {pagination.total} teachers
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPagination(prev => ({ ...prev, page: Math.max(prev.page - 1, 1) }))}
                disabled={pagination.page === 1}
                className="px-3 py-1.5 rounded-xl border outline-none text-sm font-medium"
                style={{
                  borderColor: "var(--color-border)",
                  background: "var(--color-bg-base)",
                  color: "var(--color-text-primary)",
                }}
              >
                Previous
              </button>
              <button
                onClick={() => setPagination(prev => ({ ...prev, page: Math.min(prev.page + 1, prev.pages) }))}
                disabled={pagination.page === pagination.pages}
                className="px-3 py-1.5 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:pointer-events-none"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};