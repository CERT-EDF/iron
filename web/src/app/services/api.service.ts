import { Injectable, inject } from '@angular/core';
import {
  BehaviorSubject,
  Observable,
  catchError,
  distinctUntilChanged,
  map,
  of,
  retry,
  shareReplay,
  tap,
  throwError,
} from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { UtilsService } from './utils.service';
import { AuthParams } from '../types/OIDC';
import { APIResponse, Constant, Identity, Info, User } from '../types/API';
import { Router } from '@angular/router';
import { CaseMetadata } from '../types/case';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private utils = inject(UtilsService);
  private http = inject(HttpClient);
  private router = inject(Router);
  public apiBaseUrl: string = '/api';

  private _userSubject$ = new BehaviorSubject<string>('');
  readonly user$ = this._userSubject$.asObservable();

  private infoCache: Info | undefined;
  private constantCache: Constant | undefined;
  private servicesCache: any | undefined;

  login(data: Object): Observable<APIResponse<User>> {
    return this.http.post<APIResponse<User>>(`${this.apiBaseUrl}/auth/login`, { data }).pipe(
      tap((resp) => {
        if (resp.data) this._userSubject$.next(resp.data.username);
      }),
    );
  }

  unauthorizedRedirectLogin(): void {
    this.router.navigate(['/login']);
  }

  logout(): Observable<APIResponse<null>> {
    return this.http.get<APIResponse<null>>(`${this.apiBaseUrl}/auth/logout`).pipe(
      tap(() => {
        this._userSubject$.next('');
        this.utils.toast('success', 'Logged out', 'Logged out successfully');
        this.router.navigate(['/login']);
      }),
    );
  }

  getAuthParams(): Observable<APIResponse<AuthParams>> {
    return this.http.get<APIResponse<AuthParams>>(`${this.apiBaseUrl}/auth/config`);
  }

  getInfo(): Observable<Info> {
    if (this.infoCache) return of(this.infoCache);
    return this.http.get<APIResponse<Info>>(`${this.apiBaseUrl}/info`).pipe(
      tap((resp) => (this.infoCache = resp.data)),
      map((resp) => resp.data),
    );
  }

  getConstant(): Observable<Constant> {
    if (this.constantCache) return of(this.constantCache);
    return this.http.get<APIResponse<Constant>>(`${this.apiBaseUrl}/constant`).pipe(
      tap((resp) => {
        this.constantCache = resp.data;
        if (resp.data.banner && this.utils.banner !== resp.data.banner) {
          this.utils.banner = resp.data.banner;
        }
      }),
      map((resp) => resp.data),
    );
  }

  isLogged(): Observable<boolean> {
    if (this._userSubject$.value) return of(true);
    return this.http.get<APIResponse<{ username: string }>>(`${this.apiBaseUrl}/auth/is_logged`).pipe(
      tap((resp) => {
        if (resp.data?.username) this._userSubject$.next(resp.data.username);
      }),
      map(() => true),
      distinctUntilChanged(),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }

  getServices(): Observable<any> {
    if (this.servicesCache) return of(this.servicesCache);
    return this.http.get<APIResponse<any>>(`${this.apiBaseUrl}/services`).pipe(
      tap((resp) => {
        this.servicesCache = resp.data;
      }),
      map((resp) => resp.data),
    );
  }

  getIdentities(): Observable<Identity> {
    return this.http.get<APIResponse<User[]>>(`${this.apiBaseUrl}/auth/identities`).pipe(
      map((resp) => {
        const users = resp.data.map((u) => u.username);
        const groups = Array.from(new Set(resp.data.flatMap((u) => u.groups)));
        return { users, groups };
      }),
      distinctUntilChanged(),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }

  getCase(caseGuid: string): Observable<CaseMetadata> {
    return this.http.get<APIResponse<CaseMetadata>>(`${this.apiBaseUrl}/case/${caseGuid}`).pipe(
      map((resp) => resp.data),
      distinctUntilChanged(),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }

  getCases(): Observable<CaseMetadata[]> {
    return this.http.get<APIResponse<CaseMetadata[]>>(`${this.apiBaseUrl}/cases`).pipe(
      map((resp) => {
        const previous = this.utils.getStoredCaseGuids();
        return resp.data.map((c: CaseMetadata) => ({
          ...c,
          unseenNew: previous.includes(c.guid) ? false : true,
        }));
      }),
      tap((resp) => {
        this.utils.refreshStoredCases(resp);
      }),
      distinctUntilChanged(),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }

  postCase(caseData: CaseMetadata): Observable<CaseMetadata> {
    return this.http.post<APIResponse<CaseMetadata>>(`${this.apiBaseUrl}/case`, caseData).pipe(
      tap((resp) => this.utils.addCaseGuidToStorage(resp.data.guid)),
      map((resp) => resp.data),
    );
  }

  putCase(caseGuid: string, caseData: Partial<CaseMetadata>): Observable<CaseMetadata> {
    return this.http
      .put<APIResponse<CaseMetadata>>(`${this.apiBaseUrl}/case/${caseGuid}`, caseData)
      .pipe(map((resp) => resp.data));
  }

  deleteCase(caseGuid: string): Observable<any> {
    return this.http.delete<any>(`${this.apiBaseUrl}/case/${caseGuid}`);
  }

  attachCaseService(serviceName: string, caseGuid: string, attachGuid: string): Observable<CaseMetadata> {
    return this.http
      .put<
        APIResponse<CaseMetadata>
      >(`${this.apiBaseUrl}/service/${serviceName}/case/${caseGuid}/attach/${attachGuid}`, {})
      .pipe(
        map((resp) => resp.data),
        distinctUntilChanged(),
        shareReplay({ bufferSize: 1, refCount: true }),
      );
  }

  probeCaseService(caseGuid: string, serviceName: string): Observable<CaseMetadata> {
    return this.http.get<APIResponse<CaseMetadata>>(`${this.apiBaseUrl}/service/${serviceName}/case/${caseGuid}`).pipe(
      map((resp) => resp.data),
      distinctUntilChanged(),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }

  syncCaseService(caseGuid: string, serviceName: string): Observable<CaseMetadata> {
    return this.http
      .post<APIResponse<CaseMetadata>>(`${this.apiBaseUrl}/service/${serviceName}/case/${caseGuid}`, {})
      .pipe(map((c) => c.data));
  }

  getCaseEventsSSE(guid: string): Observable<MessageEvent> {
    return new Observable<MessageEvent>((obs) => {
      const eventSource = new EventSource(`${this.apiBaseUrl}/events/case/${guid}`);
      eventSource.onmessage = (event: MessageEvent) => obs.next(event);
      eventSource.onerror = (error) => {
        this.utils.toast('error', 'EventSource disconnected', 'EventSource disconnected, reconnecting...');
        obs.error(error);
        eventSource.close();
      };
      eventSource.onopen = () => console.log('EventSource connected');
      return () => eventSource.close();
    }).pipe(
      retry({ count: 5, delay: 1000, resetOnSuccess: true }),
      catchError((error) => {
        this.utils.toast(
          'error',
          'EventSource disconnected',
          'Roses are red, Violets are blue, EventSource is disconnected, there is nothing I can do for you',
          -1,
        );
        return throwError(() => error);
      }),
    );
  }
}
