import { useMutation } from '@tanstack/react-query'
import { resolveSubdomains } from '../../api/overview'
import { Button } from '../../components/Button'
import { DataTable } from '../../components/DataTable'
import { ErrorState } from '../../components/QueryState'

interface SubdomainResolutionProps {
  uploadId: string
  rootDomain: string
  subdomains: string[]
}

/** Opt-in DNS + WHOIS report: follows each subdomain's CNAME chain to an IP,
 * then looks up who WHOIS/RDAP says owns it. Slow and network-bound, so it
 * only runs on an explicit click -- never automatically. Works for whichever
 * root domain is currently selected in the explorer, first-party or not --
 * a third-party CDN/tracker's subdomains are just as worth resolving. */
export function SubdomainResolution({ uploadId, rootDomain, subdomains }: SubdomainResolutionProps) {
  const mutation = useMutation({
    mutationFn: () => resolveSubdomains(uploadId, subdomains),
  })

  return (
    <div className="mt-3">
      <h4 className="text-sm font-semibold">DNS Resolution for `{rootDomain}` Subdomains</h4>
      <p className="my-1 mb-2 text-[13px] text-text-muted">
        Fully resolves each subdomain -- following any CNAME chain, the way <code>dig</code> would -- down to an IP
        address, then looks up who WHOIS/RDAP says owns that IP.
      </p>
      <Button onClick={() => mutation.mutate()} disabled={mutation.isPending} className="mb-2">
        {mutation.isPending ? `Resolving ${subdomains.length} subdomain(s)...` : 'Resolve subdomains'}
      </Button>

      {mutation.isError && <ErrorState label="Failed to resolve subdomains." />}

      {mutation.data && (
        <DataTable
          columns={[
            { header: 'Subdomain', accessor: (row) => row.subdomain },
            { header: 'Resolution Chain', accessor: (row) => row.chain },
            { header: 'IP Address(es)', accessor: (row) => row.ips },
            { header: 'WHOIS Organization', accessor: (row) => row.organization },
          ]}
          rows={mutation.data}
          rowKey={(row) => row.subdomain}
        />
      )}
    </div>
  )
}
