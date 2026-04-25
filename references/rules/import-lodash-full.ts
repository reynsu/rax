// ruleid: rax.perf.import-lodash-full
import _ from "lodash";

// ok: rax.perf.import-lodash-full
import { debounce } from "lodash-es";

export const a = _.debounce(() => {}, 100);
export const b = debounce(() => {}, 100);
