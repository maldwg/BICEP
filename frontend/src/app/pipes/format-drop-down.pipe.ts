import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'formatDropDown'
})
export class FormatDropDownPipe implements PipeTransform {

  transform(value: unknown, ...args: unknown[]): unknown {
    if (!value || value == null) return '';
    return value.toString().toLowerCase().replace(/-/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

}
