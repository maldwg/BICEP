import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { map } from 'rxjs/operators';
import { Observable, of as observableOf, merge, BehaviorSubject } from 'rxjs';

// TODO: Replace this with your own data model type
export interface ResultsItem {
  name: string;
  id: number;
}

// TODO: replace this with real data from your application
const EXAMPLE_DATA: ResultsItem[] = [
  {id: 1, name: 'Hydrogen'},
  {id: 2, name: 'Helium'},
  {id: 3, name: 'Lithium'},
  {id: 4, name: 'Beryllium'},
  {id: 5, name: 'Boron'},
  {id: 6, name: 'Carbon'},
  {id: 7, name: 'Nitrogen'},
  {id: 8, name: 'Oxygen'},
  {id: 9, name: 'Fluorine'},
  {id: 10, name: 'Neon'},
  {id: 11, name: 'Sodium'},
  {id: 12, name: 'Magnesium'},
  {id: 13, name: 'Aluminum'},
  {id: 14, name: 'Silicon'},
  {id: 15, name: 'Phosphorus'},
  {id: 16, name: 'Sulfur'},
  {id: 17, name: 'Chlorine'},
  {id: 18, name: 'Argon'},
  {id: 19, name: 'Potassium'},
  {id: 20, name: 'Calcium'},
];

/**
 * Data source for the Results view. This class should
 * encapsulate all logic for fetching and manipulating the displayed data
 * (including sorting, pagination, and filtering).
 */
export class ResultsDataSource extends DataSource<ResultsItem> {
  data: ResultsItem[] = EXAMPLE_DATA;
  paginator: MatPaginator | undefined;
  sort: MatSort | undefined;
  // new subject that tracks the current search text
  private filter$ = new BehaviorSubject<string>('');
  
  constructor() {
    super();
  }

  /**
   * Connect this data source to the table. The table will only update when
   * the returned stream emits new items.
   * @returns A stream of the items to be rendered.
   */
  connect(): Observable<ResultsItem[]> {
    if (!this.paginator || !this.sort) {
      throw Error('Please set the paginator and sort on the data source before connecting.');
    }

    // Merge all streams: initial data, paginator, sort, filter
    return merge(
      observableOf(this.data),           // initial data
      this.paginator.page,               // paginator events
      this.sort.sortChange,              // sort events
      this.filter$                        // filter changes
    ).pipe(
      map(() => {
        // 1️⃣ apply filtering
        const filtered = this.getFilteredData([...this.data]);

        // 2️⃣ apply sorting
        const sorted = this.getSortedData(filtered);

        // 3️⃣ apply pagination
        return this.getPagedData(sorted);
      })
    );
  }
  /**
   *  Called when the table is being destroyed. Use this function, to clean up
   * any open connections or free any held resources that were set up during connect.
   */
  disconnect(): void {}

  /** Called externally (from component) when user types in the searchbar */
  setFilter(value: string) {
    this.filter$.next(value.trim().toLowerCase());
  }
  /** Filter the data (client-side) */
private getFilteredData(data: ResultsItem[]): ResultsItem[] {
  const filterValue = this.filter$.value?.trim().toLowerCase();
  if (!filterValue) return data;

  return data.filter(item =>
    Object.values(item)
      .map(v => (v == null ? '' : String(v).toLowerCase()))
      .join(' ')
      .includes(filterValue)
  );
}
  /**
   * Paginate the data (client-side). If you're using server-side pagination,
   * this would be replaced by requesting the appropriate data from the server.
   */
private getPagedData(data: ResultsItem[]): ResultsItem[] {
  if (!this.paginator) return data;
  const startIndex = this.paginator.pageIndex * this.paginator.pageSize;
  return data.slice(startIndex, startIndex + this.paginator.pageSize); // ✅ use slice, not splice
}

  /**
   * Sort the data (client-side). If you're using server-side sorting,
   * this would be replaced by requesting the appropriate data from the server.
   */
  private getSortedData(data: ResultsItem[]): ResultsItem[] {
    if (!this.sort || !this.sort.active || this.sort.direction === '') {
      return data;
    }

    return data.sort((a, b) => {
      const isAsc = this.sort?.direction === 'asc';
      switch (this.sort?.active) {
        case 'name': return compare(a.name, b.name, isAsc);
        case 'id': return compare(+a.id, +b.id, isAsc);
        default: return 0;
      }
    });
  }
}

/** Simple sort comparator for example ID/Name columns (for client-side sorting). */
function compare(a: string | number, b: string | number, isAsc: boolean): number {
  return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
}
