import { useState, createContext, useContext } from "react";
import { useDispatch, useSelector } from "react-redux";

const Ctx = createContext<{ user?: string }>({});

export function Profile() {
  const [user, setUser] = useState<string>("a");           // local
  const ctxUser = useContext(Ctx).user;                    // context
  const reduxUser = useSelector((s: { user: string }) => s.user); // redux
  // and somewhere a window.__user assignment...
  return <p>{user ?? ctxUser ?? reduxUser}</p>;
}
