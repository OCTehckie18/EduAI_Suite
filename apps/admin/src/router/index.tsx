import { createBrowserRouter } from "react-router-dom";
import { AdminShell } from "../layouts/AdminShell";
import { AdminDashboard } from "../features/admin/AdminDashboard";
import { TeacherManagement } from "../features/admin/TeacherManagement";
import { StudentManagement } from "../features/admin/StudentManagement";
import { AdminUsersPage } from "../features/admin/AdminUsersPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AdminShell />,
    children: [
      { index: true, element: <AdminDashboard /> },
      { path: "dashboard", element: <AdminDashboard /> },
      { path: "teachers", element: <TeacherManagement /> },
      { path: "students", element: <StudentManagement /> },
      { path: "admin/users", element: <AdminUsersPage /> },
    ],
  },
]);