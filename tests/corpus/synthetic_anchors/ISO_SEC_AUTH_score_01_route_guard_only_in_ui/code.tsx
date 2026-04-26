import { useAuth } from "./auth";
export function AdminPage() {
  const { user } = useAuth();
  if (!user?.isAdmin) return <p>access denied</p>;
  return <UserList />;
}
function UserList() {
  return <ul />;
}
