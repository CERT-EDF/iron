import { HttpErrorResponse, HttpEvent, HttpHandlerFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';
import { UtilsService } from './utils.service';
import { ApiService } from './api.service';

export const Interceptor = (req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> => {
  const apiService = inject(ApiService);
  const utilsService = inject(UtilsService);

  if (!req.headers.has('Content-Type')) {
    req = req.clone({ setHeaders: { 'Content-Type': 'application/json' } });
  }

  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      switch (err.status) {
        case 400:
          console.error(err);
          utilsService.toast('error', 'Bad Request', `${err.error || 'Unknown error, check console for details'}`);
          break;

        case 401:
          apiService.unauthorizedRedirectLogin();
          break;

        case 403:
          utilsService.toast('error', 'Forbidden', 'You are not allowed to do this', 3500);
          break;

        case 404:
          utilsService.toast(
            'error',
            'Not found',
            `${err.error.message || err.message || 'Entity not found, check console for details'}`,
            3500,
          );
          break;

        case 502:
          utilsService.toast('error', 'Bad Gateway', 'Verify the server is up and running');
          apiService.unauthorizedRedirectLogin();
          return throwError(() => new Error(`Bad Gateway: ${err.error || 'Unknown error, check console for details'}`));

        default:
          break;
      }

      return throwError(() => err);
    }),
  );
};
