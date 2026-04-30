import { Outlet } from "react-router-dom";
import Navbar from "../../components/Navbarbb";
import Sidebar from "../../components/Sidebar";

export default function AutoMLLayout() {
  return (
    <div className="page">
      <Navbar />
      <div className="automl-layout">
        <Sidebar />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
