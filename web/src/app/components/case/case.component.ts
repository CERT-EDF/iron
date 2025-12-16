import { ChangeDetectorRef, Component, ViewChild } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { FloatLabelModule } from 'primeng/floatlabel';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';
import { SkeletonModule } from 'primeng/skeleton';
import { ApiService } from '../../services/api.service';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ClipboardModule } from '@angular/cdk/clipboard';
import { DialogService } from 'primeng/dynamicdialog';
import { Menu, MenuModule } from 'primeng/menu';
import { TooltipModule } from 'primeng/tooltip';
import { CaseMetadata, FusionEvent } from '../../types/case';
import { UtilsService } from '../../services/utils.service';
import { MenuItem } from 'primeng/api';
import { catchError, forkJoin, map, of, Subscription, take, tap } from 'rxjs';
import { Service } from '../../types/API';
import { WebhookModalComponent } from '../../modals/webhook-modal/webhook-modal.component';
import { AttachModalComponent } from '../../modals/attach-modal/attach-modal.component';
import { CaseCreateModalComponent } from '../../modals/case-create-modal/case-create-modal.component';
import { DeleteConfirmModalComponent } from '../../modals/delete-confirm-modal/delete-confirm-modal.component';

@Component({
  selector: 'app-case',
  standalone: true,
  imports: [
    RouterLink,
    FloatLabelModule,
    InputTextModule,
    ButtonModule,
    SelectModule,
    ReactiveFormsModule,
    SkeletonModule,
    TextareaModule,
    ClipboardModule,
    MenuModule,
    ButtonModule,
    TooltipModule,
  ],
  templateUrl: './case.component.html',
  styleUrl: './case.component.scss',
})
export class CaseComponent {
  @ViewChild('caseMenu') caseMenu!: Menu;
  caseForm: FormGroup;
  caseMeta!: CaseMetadata;
  services: Service[] = [];
  caseMenuItems: MenuItem[] = [];
  eventSource!: Subscription;
  activeUsers: string[] = [];

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef,
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private utilsService: UtilsService,
    private dialogService: DialogService,
  ) {
    this.caseForm = this.fb.group({
      tsid: '',
      name: ['', Validators.required],
      description: '',
    });

    forkJoin({
      services: this.apiService.getServices(),
      caseMeta: this.apiService.getCase(this.route.snapshot.paramMap.get('id')!),
    })
      .pipe(
        take(1),
        tap(({ services, caseMeta }) => {
          this.services = services;
          this.caseMeta = caseMeta;

          this.eventSource = this.apiService.getCaseEventsSSE(this.caseMeta!.guid).subscribe({
            next: (event) => this.handleSSEEvent(event),
            error: (error) => console.error('SSE error:', error),
          });
        }),
      )
      .subscribe({
        next: () => this.probeCaseServices(),
        error: () => this.utilsService.navigateHomeWithError('Error while retrieving case'),
      });
  }

  handleSSEEvent(messageEvent: MessageEvent): void {
    if (!messageEvent.data) return;
    const event: FusionEvent = JSON.parse(messageEvent.data);
    const ext = event.ext;
    switch (event.category) {
      case 'subscribers':
        this.activeUsers = ext.usernames;
        break;
      case 'subscribe':
        if (!this.activeUsers.includes(ext.username)) this.activeUsers.push(ext.username);
        break;
      case 'unsubscribe':
        this.activeUsers = this.activeUsers.filter((u) => u !== ext.username);
        break;
      case 'service_delete_case':
        this.probeCaseServices();
        break;
      case 'update_case':
        this.caseMeta = event.case;
        break;
      case 'delete_case':
        this.utilsService.toast('info', 'Case deleted', 'This case was deleted');
        this.utilsService.navigateHomeWithError();
        break;
      default:
        if (!event.category.startsWith('service_')) break;
        const service = this.services.find((s) => s.name === ext.service);
        if (!service) break;
        service.case_data = event.case as CaseMetadata;
        service.status = this.computeCaseStatus(event.case);
        break;
    }
    this.cdr.markForCheck();
  }

  computeCaseStatus(serviceCaseMeta: CaseMetadata | null): string {
    const ironCase = this.caseMeta;
    if (!serviceCaseMeta) return 'Missing';
    if (ironCase.closed && serviceCaseMeta.closed) return 'Closed';
    if (ironCase.closed && !serviceCaseMeta.closed) return 'Outdated';
    if (!ironCase.updated && serviceCaseMeta.updated) return 'Synced';
    if (!ironCase.updated && !serviceCaseMeta.updated) return 'Synced';
    if (ironCase.updated && !serviceCaseMeta.updated) return 'Outdated';
    if (ironCase.updated && serviceCaseMeta.updated && ironCase.updated > serviceCaseMeta.updated) return 'Outdated';
    if (ironCase.updated && serviceCaseMeta.updated && ironCase.updated <= serviceCaseMeta.updated) return 'Synced';
    return 'Invalid';
  }

  probeCaseServices() {
    const observables$ = this.services.map((service) =>
      this.apiService.probeCaseService(this.caseMeta.guid, service.name).pipe(
        map((serviceCaseMeta) => ({
          serviceName: service.name,
          serviceCaseMeta,
        })),
        catchError(() => of({ serviceName: service.name, serviceCaseMeta: null })),
      ),
    );

    forkJoin(observables$)
      .pipe(take(1))
      .subscribe({
        next: (items) => {
          items.forEach((item) => {
            const service = this.services.find((s) => s.name === item.serviceName);
            if (service) {
              service.status = this.computeCaseStatus(item.serviceCaseMeta);
              service.case_data = item.serviceCaseMeta as CaseMetadata;
            }
          });
        },
      });
  }

  openServiceCase(service: Service) {
    const baseUrl = service.api_url.replace(/\/+$/, '');
    const xref = service.xref.startsWith('/')
      ? service.xref.replace('{case.guid}', this.caseMeta.guid)
      : '/' + service.xref.replace('{case.guid}', this.caseMeta.guid);
    const fullUrl = baseUrl + xref;
    window.open(fullUrl, '_blank');
  }

  refreshServices() {
    const iconElement = document.getElementById('refreshIcon');
    iconElement?.classList.add('spin-once');
    setTimeout(() => {
      iconElement?.classList.remove('spin-once');
    }, 1000);

    this.probeCaseServices();
  }

  syncServices() {
    const iconElement = document.getElementById('syncIcon');
    iconElement?.classList.add('spin-once');
    setTimeout(() => {
      iconElement?.classList.remove('spin-once');
    }, 1000);

    const observables$ = this.services.map((service) =>
      this.apiService.syncCaseService(this.caseMeta.guid, service.name).pipe(
        map((result) => ({ serviceName: service.name, result })),
        catchError(() => of({ serviceName: service.name, result: null })),
      ),
    );

    forkJoin(observables$)
      .pipe(take(1))
      .subscribe({
        next: (items) => {
          items.forEach((item) => {
            const service = this.services.find((service) => service.name === item.serviceName);
            if (!service) return;
            service.status = this.computeCaseStatus(item.result);
            service.case_data = item.result as CaseMetadata;
          });
        },
      });
  }

  syncService(service: Service) {
    const iconElement = document.getElementById(`${service.name}Icon`);
    iconElement?.classList.add('spin-once');
    setTimeout(() => {
      iconElement?.classList.remove('spin-once');
    }, 1000);

    this.apiService
      .syncCaseService(this.caseMeta.guid, service.name)
      .pipe(take(1))
      .subscribe({
        next: (data) => {
          const _service = this.services.find((s) => s.name === service.name);
          if (!_service) return;
          service.status = this.computeCaseStatus(data);
          service.case_data = data;
        },
      });
  }

  constructCaseMenu(ev: any) {
    if (!this.caseMeta) return;
    const closeOrReopenItem = this.caseMeta.closed
      ? {
          label: 'Reopen',
          icon: 'pi pi-lock-open',
          iconClass: 'text-green-500!',
          command: () =>
            this.apiService
              .putCase(this.caseMeta!.guid, { closed: '' })
              .pipe(take(1))
              .subscribe({
                next: (meta) => (this.caseMeta = meta),
              }),
        }
      : {
          label: 'Close',
          icon: 'pi pi-times',
          iconClass: 'text-red-500!',
          command: () =>
            this.apiService
              .putCase(this.caseMeta!.guid, { closed: new Date().toISOString() })
              .pipe(take(1))
              .subscribe({
                next: (meta) => (this.caseMeta = meta),
              }),
        };

    this.caseMenuItems = [
      {
        label: 'Copy GUID',
        icon: 'pi pi-tag',
        command: () => {
          try {
            navigator.clipboard.writeText(this.caseMeta!.guid);
          } catch {
            console.error('Clipboard not available');
            this.utilsService.toast('error', 'Error', 'Clipboard not available');
          }
        },
      },
      {
        label: 'Edit',
        icon: 'pi pi-pencil',
        disabled: !!this.caseMeta.closed,
        command: () => this.openEditCaseModal(),
      },
      closeOrReopenItem,
      {
        label: 'Delete',
        icon: 'pi pi-trash',
        iconClass: 'text-red-500!',
        command: () => this.deleteCase(),
      },
    ];
    this.caseMenu.toggle(ev);
  }

  openEditCaseModal() {
    let modal = this.dialogService.open(CaseCreateModalComponent, {
      header: 'Update Case',
      modal: true,
      appendTo: 'body',
      closable: true,
      dismissableMask: true,
      width: '30vw',
      data: this.caseMeta,
      breakpoints: {
        '960px': '90vw',
      },
    });

    modal.onClose.pipe(take(1)).subscribe((data: CaseMetadata | null) => {
      if (!data) return;
      this.updateCase(data);
    });
  }

  updateCase(data: Partial<CaseMetadata>) {
    this.apiService.putCase(this.caseMeta!.guid, data).pipe(take(1)).subscribe();
  }

  deleteCase() {
    if (!this.caseMeta || !this.caseMeta.name) return;
    const modal = this.dialogService.open(DeleteConfirmModalComponent, {
      header: 'Confirm to delete',
      modal: true,
      closable: true,
      dismissableMask: true,
      breakpoints: {
        '640px': '90vw',
      },
      data: this.caseMeta?.name,
    });

    modal.onClose.pipe(take(1)).subscribe((confirmed: boolean) => {
      if (!confirmed) return;
      this.apiService.deleteCase(this.caseMeta!.guid).pipe(take(1)).subscribe();
    });
  }

  attachService(service: Service) {
    let modal = this.dialogService.open(AttachModalComponent, {
      header: 'Attach ' + service.name,
      modal: true,
      appendTo: 'body',
      closable: true,
      dismissableMask: true,
      width: '50vw',
      breakpoints: {
        '960px': '90vw',
      },
    });

    modal.onClose.pipe(take(1)).subscribe((guid: string) => {
      if (!guid) return;
      this.apiService.attachCaseService(service.name, guid, this.caseMeta!.guid).pipe(take(1)).subscribe();
    });
  }

  addWebhook() {
    let modal = this.dialogService.open(WebhookModalComponent, {
      header: 'Add webhook',
      modal: true,
      appendTo: 'body',
      closable: true,
      dismissableMask: true,
      width: '50vw',
      breakpoints: {
        '960px': '90vw',
      },
    });

    modal.onClose.pipe(take(1)).subscribe((webhook: string | null) => {
      if (!webhook) return;
      const wh = [...this.caseMeta.webhooks, webhook];
      this.updateCase({ webhooks: wh });
    });
  }

  deleteWebhook(webhook: string) {
    const wh = this.caseMeta.webhooks.filter((w) => w != webhook);
    this.updateCase({ webhooks: wh });
  }

  deleteWebhooks() {
    this.updateCase({ webhooks: [] });
  }
}
