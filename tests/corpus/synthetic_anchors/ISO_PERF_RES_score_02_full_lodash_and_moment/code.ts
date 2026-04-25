import _ from "lodash";        // ~70 kB
import moment from "moment";    // ~290 kB w/ locales

export function format(d: Date, items: string[]) {
  return _.uniq(items).map(i => `${moment(d).format()} - ${i}`);
}
