import React, { useEffect, useState } from "react";
import {
  Users,
  AlertCircle,
  Activity,
  LayoutDashboard,
  BarChart3,
  Loader2,
  CheckCircle,
  XCircle
} from "lucide-react";
import { API_ENDPOINTS } from "../../shared/utils/apiConfig";

interface Stats {
  totalTeachers: number;
  totalStudents: number;
  pendingApprovals: number;
  activeUsers: number;
}

interface RecentActivity {
  id: number;
  type: string;
  description: string;
  timestamp: string;
  userName: string;
}

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats>({
    totalTeachers: 0,
    totalStudents: 0,
    pendingApprovals: 0,
    activeUsers: 0
  });

  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      const storedToken = localStorage.getItem("token");

      // Fetch stats
      const statsRes = await fetch(`${API_ENDPOINTS.BASE}/admin/dashboard-stats`, {
        headers: {
          Authorization: `Bearer ${storedToken}`,
        },
      });

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      // Fetch recent activity
      const activityRes = await fetch(`${API_ENDPOINTS.BASE}/admin/recent-activity`, {
        headers: {
          Authorization: `Bearer ${storedToken}`,
        },
      });

      if (activityRes.ok) {
        const activityData = await activityRes.json();
        setRecentActivity(activityData);
      }
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
      setError("Failed to load dashboard data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto animate-fade-in">
        <div className="grid gap-6 md:grid-cols-2">
          {/* Loading placeholders */}
          <div className="glass-card border p-6" style={{
            borderColor: "var(--color-border)",
            background: "var(--color-surface-card)"
          }}>
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <LayoutDashboard size={20} className="text-blue-500" />
              Dashboard Overview
            </h2>
            <div className="space-y-4">
              {[1, 2, 3, 4].map((_, i) => (
                <div key={i} className="h-4 bg-gray-200 rounded w-full animate-pulse"></div>
              ))}
            </div>
          </div>

          <div className="glass-card border p-6" style={{
            borderColor: "var(--color-border)",
            background: "var(--color-surface-card)"
          }}>
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Activity size={20} className="text-green-500" />
              Recent Activity
            </h2>
            <div className="space-y-3">
              {[1, 2, 3].map((_, i) => (
                <div key={i} className="h-4 bg-gray-200 rounded w-full animate-pulse"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto animate-fade-in">
        <div className="glass-card border p-6" style={{
          borderColor: "var(--color-border)",
          background: "var(--color-surface-card)"
        }}>
          <div className="flex items-start gap-4">
            <AlertCircle size={20} className="text-red-500 mt-1" />
            <div>
              <h2 className="font-bold text-lg mb-2">Error Loading Dashboard</h2>
              <p className="text-sm">{error}</p>
              <button
                onClick={fetchDashboardData}
                className="mt-3 btn btn-sm btn-primary"
              >
                Retry
              </button>
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
            Admin Dashboard
          </h1>
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
            Overview of EduAI Suite user management and system statistics
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 mb-8 md:grid-cols-2 lg:grid-cols-4">
        {/* Total Teachers */}
        <div className="glass-card border p-6" style={{
          borderColor: "var(--color-border)",
          background: "var(--color-surface-card)"
        }}>
          <div className="flex items-start gap-4">
            <Users size={24} className="text-blue-500 flex-shrink-0" />
            <div>
              <h2 className="text-lg font-bold mb-1">Total Teachers</h2>
              <p className="text-2xl font-black">{stats.totalTeachers}</p>
            </div>
          </div>
        </div>

        {/* Total Students */}
        <div className="glass-card border p-6" style={{
          borderColor: "var(--color-border)",
          background: "var(--color-surface-card)"
        }}>
          <div className="flex items-start gap-4">
            <Users size={24} className="text-green-500 flex-shrink-0" />
            <div>
              <h2 className="text-lg font-bold mb-1">Total Students</h2>
              <p className="text-2xl font-black">{stats.totalStudents}</p>
            </div>
          </div>
        </div>

        {/* Pending Approvals */}
        <div className="glass-card border p-6" style={{
          borderColor: "var(--color-border)",
          background: "var(--color-surface-card)"
        }}>
          <div className="flex items-start gap-4">
            <AlertCircle size={24} className="text-yellow-500 flex-shrink-0" />
            <div>
              <h2 className="text-lg font-bold mb-1">Pending Approvals</h2>
              <p className="text-2xl font-black">{stats.pendingApprovals}</p>
            </div>
          </div>
        </div>

        {/* Active Users */}
        <div className="glass-card border p-6" style={{
          borderColor: "var(--color-border)",
          background: "var(--color-surface-card)"
        }}>
          <div className="flex items-start gap-4">
            <CheckCircle size={24} className="text-teal-500 flex-shrink-0" />
            <div>
              <h2 className="text-lg font-bold mb-1">Active Users</h2>
              <p className="text-2xl font-black">{stats.activeUsers}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="glass-card border" style={{
        borderColor: "var(--color-border)"
      }}>
        <div className="p-4 border-b" style={{ borderColor: "var(--color-border)" }}>
          <h2 className="font-bold flex items-center gap-2">
            <Activity size={18} style={{ color: "var(--color-brand-blue)" }} />
            Recent Activity
          </h2>
        </div>

        {recentActivity.length === 0 ? (
          <div className="p-8 text-center">
            <Activity size={32} className="mx-auto mb-4 opacity-20" />
            <p className="text-gray-500 font-semibold text-lg">No recent activity</p>
            <p className="text-sm text-gray-400">Activity will appear here as users interact with the system.</p>
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--color-border)" }}>
            {recentActivity.map((activity) => (
              <div key={activity.id} className="p-4 flex items-start gap-4">
                <div className="flex-shrink-0">
                  {activity.type === "teacher_added" && (
                    <Users size={20} className="text-blue-500" />
                  )}
                  {activity.type === "student_added" && (
                    <Users size={20} className="text-green-500" />
                  )}
                  {activity.type === "user_approved" && (
                    <CheckCircle size={20} className="text-green-500" />
                  )}
                  {activity.type === "user_denied" && (
                    <XCircle size={20} className="text-red-500" />
                  )}
                  {activity.type === "user_updated" && (
                    <Activity size={20} className="text-yellow-500" />
                  )}
                </div>
                <div className="flex-1 space-y-1">
                  <p className="font-medium text-sm">{activity.description}</p>
                  <p className="text-xs text-gray-500">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};