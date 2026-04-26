// ruleid: rax.perf.import-moment
import moment from "moment";

// ok: rax.perf.import-moment
import { format } from "date-fns";

export const a = moment().format();
export const b = format(new Date(), "yyyy-MM-dd");
