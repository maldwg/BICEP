import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { BehaviorSubject, merge, Observable, of as observableOf, of } from 'rxjs';
import { catchError, map, startWith, switchMap } from 'rxjs/operators';
import { BenchmarkingResultsItem } from '../../models/benchmarking';
import { BenchmarkingService } from './benchmarking.service';

/**
 * Data source for the Results view. This class should
 * encapsulate all logic for fetching and manipulating the displayed data
 * (including sorting, pagination, and filtering).
 */
export class ResultsDataSource extends DataSource<BenchmarkingResultsItem> {
  paginator: MatPaginator | undefined;
  sort: MatSort | undefined;
  // new subject that tracks the current search text
  private filter$ = new BehaviorSubject<string>('');
  private dataSubject = new BehaviorSubject<BenchmarkingResultsItem[]>([]);

  constructor(private benchmarkingService: BenchmarkingService) {
    super();
  }

  /**
   * Connect this data source to the table. The table will only update when
   * the returned stream emits new items.
   * @returns A stream of the items to be rendered.
   */
  connect(): Observable<BenchmarkingResultsItem[]> {
    if (!this.paginator || !this.sort) {
      throw Error('Please set the paginator and sort on the data source before connecting.');
    }

    // Merge all streams: initial data, paginator, sort, filter
    return merge(this.paginator.page, this.sort.sortChange, this.filter$).pipe(
      startWith({}),
      switchMap(() =>
        this.benchmarkingService.getAllConfigurations().pipe(
          catchError(() => of([]))
        )
      ),
      map((data) => {
        const filtered = this.getFilteredData([...data]);
        const sorted = this.getSortedData(filtered);
        const paged = this.getPagedData(sorted);
        this.dataSubject.next(paged);
        return paged;
      })
    );
  }
  /**
   *  Called when the table is being destroyed. Use this function, to clean up
   * any open connections or free any held resources that were set up during connect.
   */
  disconnect(): void {
    this.dataSubject.complete();
    this.filter$.complete();
  }
  /** Called externally (from component) when user types in the searchbar */
  setFilter(value: string) {
    this.filter$.next(value.trim().toLowerCase());
  }
  /** Filter the data (client-side) */
private getFilteredData(data: BenchmarkingResultsItem[]): BenchmarkingResultsItem[] {
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
private getPagedData(data: BenchmarkingResultsItem[]): BenchmarkingResultsItem[] {
  if (!this.paginator) return data;
  const startIndex = this.paginator.pageIndex * this.paginator.pageSize;
  return data.slice(startIndex, startIndex + this.paginator.pageSize); // ✅ use slice, not splice
}

  /**
   * Sort the data (client-side). If you're using server-side sorting,
   * this would be replaced by requesting the appropriate data from the server.
   */
  private getSortedData(data: BenchmarkingResultsItem[]): BenchmarkingResultsItem[] {
    if (!this.sort || !this.sort.active || this.sort.direction === '') {
      return data;
    }

    return data.sort((a, b) => {
      const isAsc = this.sort?.direction === 'asc';
      switch (this.sort?.active) {
        case 'ids_name': return compare(a.ids_name, b.ids_name, isAsc);
        case 'dataset_name': return compare(+a.id, +b.id, isAsc);
        case 'ensembnling_method': return compare(a.ids_name, b.ids_name, isAsc);
        case 'acc': return compare(+a.id, +b.id, isAsc);
        case 'prec': return compare(a.ids_name, b.ids_name, isAsc);
        case 'fnr': return compare(+a.id, +b.id, isAsc);
        case 'fdr': return compare(a.ids_name, b.ids_name, isAsc);
        case 'fpr': return compare(+a.id, +b.id, isAsc);
        case 'f1_score': return compare(a.ids_name, b.ids_name, isAsc);
        case 'detection_rate': return compare(+a.id, +b.id, isAsc);
        case 'start_time': return compare(+a.id, +b.id, isAsc);
        case 'stop_time': return compare(a.ids_name, b.ids_name, isAsc);
        case 'runtime': return compare(+a.id, +b.id, isAsc);
        default: return 0;
      }
    });
  }
}

/** Simple sort comparator for example ID/Name columns (for client-side sorting). */
function compare(a: string | number, b: string | number, isAsc: boolean): number {
  return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
}
